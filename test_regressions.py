"""Regression tests for bugs found in the code review. Every test here failed before the fixes."""

import subprocess
import sys
import unittest
from datetime import date
from unittest import mock

from engine import agent
from engine.agent import generate_offline_agent_insight, generate_llm_agent_insight
from engine.matcher import (
    compare_skills, check_branch_eligibility, check_cgpa_eligibility,
    check_eligibility, evaluate_opportunities, compute_deadline_info,
)
from engine.sources import (
    BaseOpportunitySource, JsonOpportunitySource, OpportunityRepository, sanitize_opportunity,
)

STUDENT = {"name": "Dev", "year": "3rd Year", "branch": "Computer Science", "cgpa": 8.4,
           "skills": ["Python", "Data Structures"], "interests": [], "preferred_types": [], "preferred_mode": "Any"}


class TestMatcherRegressions(unittest.TestCase):
    def test_no_substring_skill_false_positives(self):
        for have, need in [("Java", "JavaScript"), ("GitHub", "Git"), ("SQL", "NoSQL"), ("C", "C++"), ("Go", "Django")]:
            self.assertEqual(compare_skills([have], [need])["matched_skills"], [], f"{have} must not match {need}")

    def test_aliases_still_work(self):
        self.assertEqual(compare_skills(["DSA", "cpp"], ["Data Structures", "C++"])["match_percentage"], 100.0)

    def test_blank_branch_is_not_eligible(self):
        self.assertFalse(check_branch_eligibility("", ["Computer Science"])[0])
        self.assertTrue(check_branch_eligibility("", ["All Engineering Branches"])[0])
        self.assertFalse(check_branch_eligibility("Engineering", ["Computer Science"])[0])

    def test_bad_inputs_do_not_crash(self):
        self.assertTrue(check_cgpa_eligibility("abc", 0)[0])
        self.assertFalse(check_cgpa_eligibility("abc", 7)[0])
        check_eligibility(STUDENT, {"min_cgpa": None})
        evaluate_opportunities({"skills": None, "preferred_types": None, "interests": None,
                                "year": "2nd Year", "branch": "CSE", "cgpa": 8}, [{"title": "x", "skills": ["a"]}])
        generate_offline_agent_insight({"cgpa": "abc"}, {"title": "x"})

    def test_expired_opportunities_rank_last_and_are_flagged(self):
        opps = [
            {"id": "old", "title": "Old", "skills": ["Python", "Data Structures"], "deadline": "2026-01-01"},
            {"id": "new", "title": "New", "skills": [], "deadline": "2026-12-01"},
        ]
        ranked = evaluate_opportunities(STUDENT, opps, reference_date=date(2026, 10, 4))
        self.assertEqual([o["id"] for o in ranked], ["new", "old"])
        self.assertTrue(ranked[1]["is_expired"])

    def test_closing_soon_threshold_is_consistent(self):
        self.assertEqual(compute_deadline_info("2026-10-09", date(2026, 10, 4))["status"], "Closing Soon")  # 5 days
        self.assertEqual(compute_deadline_info("2026-10-10", date(2026, 10, 4))["status"], "Approaching Deadline")

    def test_pan_india_defaults_to_remote(self):
        ev = evaluate_opportunities(STUDENT, [{"title": "x", "location": "Pan-India"}])[0]
        self.assertEqual(ev["mode"], "Remote")


class TestAgentRegressions(unittest.TestCase):
    def test_no_required_skills_message_is_not_contradictory(self):
        ev = evaluate_opportunities(STUDENT, [{"title": "Open Contest", "skills": []}])[0]
        self.assertNotIn("0%", generate_offline_agent_insight(STUDENT, ev)["skill_alignment"])

    def test_ineligible_actions_do_not_say_submit(self):
        bad = dict(STUDENT, year="1st Year")
        ev = evaluate_opportunities(bad, [{"title": "x", "eligible_years": ["3rd Year"], "deadline": "2030-01-01"}])[0]
        actions = generate_offline_agent_insight(bad, ev)["recommended_next_actions"]
        self.assertFalse(any("Submit official application" in a["task"] for a in actions))

    def test_expired_actions_do_not_say_submit(self):
        ev = evaluate_opportunities(STUDENT, [{"title": "x", "deadline": "2020-01-01"}], date(2026, 10, 4))[0]
        actions = generate_offline_agent_insight(STUDENT, ev)["recommended_next_actions"]
        self.assertIn("passed", actions[2]["task"])

    def _ineligible_eval(self):
        bad = dict(STUDENT, year="1st Year")
        return bad, evaluate_opportunities(bad, [{"title": "x", "eligible_years": ["3rd Year"]}])[0]

    def test_llm_cannot_override_ineligible_verdict(self):
        bad, ev = self._ineligible_eval()
        reply = ('{"why_recommended": "Great news, you are eligible!", "skill_alignment": "You are eligible and a perfect fit.",'
                 ' "eligibility_explanation": "You are eligible.", "missing_skills": "none",'
                 ' "recommended_next_actions": [{"phase":"1","task":"a","detail":"b"},{"phase":"2","task":"a","detail":"b"},{"phase":"3","task":"a","detail":"b"}]}')
        fake = mock.MagicMock()
        fake.models.generate_content.return_value = mock.MagicMock(text=reply)
        with mock.patch.object(agent, "HAS_GENAI", True), mock.patch.object(agent, "genai", create=True) as g:
            g.Client.return_value = fake
            out = generate_llm_agent_insight(bad, ev, api_key="k")
        self.assertIn("INELIGIBLE", out["eligibility_explanation"])
        self.assertIn("Not Recommended", out["why_recommended"])
        self.assertNotIn("you are eligible", out["skill_alignment"].lower())

    def test_llm_garbage_and_missing_library_fall_back(self):
        bad, ev = self._ineligible_eval()
        fake = mock.MagicMock()
        fake.models.generate_content.return_value = mock.MagicMock(text="not json at all")
        with mock.patch.object(agent, "HAS_GENAI", True), mock.patch.object(agent, "genai", create=True) as g:
            g.Client.return_value = fake
            out = generate_llm_agent_insight(bad, ev, api_key="k")
        self.assertIn("Deterministic", out["engine_mode"])
        self.assertNotIn("not json", out["why_recommended"])
        with mock.patch.object(agent, "HAS_GENAI", False):
            self.assertIn("not installed", generate_llm_agent_insight(bad, ev, api_key="k")["engine_mode"])

    def test_llm_exception_falls_back_with_visible_reason(self):
        bad, ev = self._ineligible_eval()
        with mock.patch.object(agent, "HAS_GENAI", True), mock.patch.object(agent, "genai", create=True) as g:
            g.Client.side_effect = RuntimeError("quota")
            out = generate_llm_agent_insight(bad, ev, api_key="k")
        self.assertIn("Gemini unavailable", out["engine_mode"])

    def test_prompt_excludes_student_name(self):
        _, ev = self._ineligible_eval()
        fake = mock.MagicMock()
        fake.models.generate_content.return_value = mock.MagicMock(text="{}")
        with mock.patch.object(agent, "HAS_GENAI", True), mock.patch.object(agent, "genai", create=True) as g:
            g.Client.return_value = fake
            generate_llm_agent_insight(dict(STUDENT, name="SecretName Person"), ev, api_key="k")
        self.assertNotIn("SecretName", fake.models.generate_content.call_args.kwargs["contents"])


class TestSourceRegressions(unittest.TestCase):
    def test_title_none_rejected(self):
        self.assertIsNone(sanitize_opportunity({"title": None}))

    def test_generated_ids_are_stable_across_processes(self):
        code = "from engine.sources import sanitize_opportunity as s;print(s({'title':'Hack X','organization':'Org'})['id'])"
        ids = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout.strip() for _ in range(3)}
        self.assertEqual(len(ids), 1)

    def test_unsafe_urls_are_neutralised(self):
        for bad in ["javascript:alert(1)", "data:text/html,x", "ftp://x"]:
            self.assertEqual(sanitize_opportunity({"title": "x", "application_url": bad})["application_url"], "#")
        self.assertEqual(sanitize_opportunity({"title": "x", "application_url": "https://ok.com"})["application_url"], "https://ok.com")

    def test_mode_and_domain_tags_preserved(self):
        s = sanitize_opportunity({"title": "x", "mode": "Remote", "domain_tags": ["AI"]})
        self.assertEqual((s["mode"], s["domain_tags"]), ("Remote", ["AI"]))

    def test_repository_sanitizes_custom_sources(self):
        class Raw(BaseOpportunitySource):
            def __init__(self): super().__init__("Raw", True)
            def fetch_opportunities(self, category=None): return [{"title": "No id here"}, {"nonsense": 1}]
        repo = OpportunityRepository(JsonOpportunitySource())
        repo.register_source(Raw())
        items, status = repo.get_opportunities()
        self.assertIn("Raw", status["sources_succeeded"])
        self.assertTrue(any(i["title"] == "No id here" for i in items))

    def test_missing_json_is_reported_not_silent(self):
        from pathlib import Path
        _, status = OpportunityRepository(JsonOpportunitySource(Path("/definitely/missing.json"))).get_opportunities()
        self.assertIn("Local JSON Storage", status["sources_failed"])

    def test_category_filter_is_exact(self):
        self.assertEqual(JsonOpportunitySource().fetch_opportunities("s"), [])
        self.assertEqual(JsonOpportunitySource().fetch_opportunities("zzz"), [])


if __name__ == "__main__":
    unittest.main()
