"""
Unit Tests for Deterministic & Explainable Opportunity Matching Engine.
Covers all 8 functional requirements.
"""

import unittest
from datetime import date
from engine.matcher import (
    compare_skills,
    check_year_eligibility,
    check_branch_eligibility,
    check_cgpa_eligibility,
    check_eligibility,
    calculate_match_score,
    evaluate_opportunities
)


class TestOpportunityMatchingEngine(unittest.TestCase):

    # Req 1, 2, 6, 7: Skill Comparison, Match %, Matched & Missing Skills
    def test_skill_comparison_and_match_percentage(self):
        student_skills = ["Python", "DSA", "git", "React"]
        required_skills = ["Python", "Data Structures", "Algorithms", "C++"]
        
        result = compare_skills(student_skills, required_skills)
        
        # 'DSA' maps to 'Data Structures', 'Python' matches 'Python'
        self.assertIn("Python", result["matched_skills"])
        self.assertIn("Data Structures", result["matched_skills"])
        self.assertIn("Algorithms", result["missing_skills"])
        self.assertIn("C++", result["missing_skills"])
        
        # 2 out of 4 skills matched = 50.0%
        self.assertEqual(result["match_percentage"], 50.0)
        self.assertIn("Matched 2 of 4", result["explanation"])

    # Req 3: Year Eligibility Check
    def test_year_eligibility(self):
        # Passed case
        ok, reason = check_year_eligibility("3rd Year", ["2nd Year", "3rd Year"])
        self.assertTrue(ok)
        self.assertIn("Eligible", reason)

        # Ineligible case
        ok_fail, reason_fail = check_year_eligibility("1st Year", ["3rd Year", "4th Year"])
        self.assertFalse(ok_fail)
        self.assertIn("Ineligible", reason_fail)

        # Wildcard case
        ok_wild, _ = check_year_eligibility("2nd Year", ["All Years"])
        self.assertTrue(ok_wild)

    # Req 4: Branch Eligibility Check
    def test_branch_eligibility(self):
        # Exact branch
        ok, reason = check_branch_eligibility("Computer Science", ["Computer Science", "Information Technology"])
        self.assertTrue(ok)

        # Abbreviation / Synonym (CSE -> Computer Science)
        ok_alias, reason_alias = check_branch_eligibility("CSE", ["Computer Science"])
        self.assertTrue(ok_alias)

        # All Engineering Branches wildcard
        ok_wild, reason_wild = check_branch_eligibility("Electrical Engineering", ["All Engineering Branches"])
        self.assertTrue(ok_wild)

        # Ineligible branch
        ok_fail, reason_fail = check_branch_eligibility("Mechanical Engineering", ["Computer Science", "Information Technology"])
        self.assertFalse(ok_fail)

    # Req 5: CGPA Eligibility Check
    def test_cgpa_eligibility(self):
        # Exceeds cutoff
        ok, reason = check_cgpa_eligibility(8.5, 7.5)
        self.assertTrue(ok)

        # Below cutoff
        ok_fail, reason_fail = check_cgpa_eligibility(7.2, 7.5)
        self.assertFalse(ok_fail)

        # No cutoff required (0.0)
        ok_zero, _ = check_cgpa_eligibility(6.0, 0.0)
        self.assertTrue(ok_zero)

        # CGPA omitted when cutoff required
        ok_none, reason_none = check_cgpa_eligibility(None, 7.0)
        self.assertFalse(ok_none)

    # Req 8: Relevance-based Ranking
    def test_relevance_ranking(self):
        student = {
            "name": "Dev",
            "year": "3rd Year",
            "branch": "Computer Science",
            "cgpa": 8.0,
            "skills": ["Python", "Data Structures", "Algorithms", "C++"],
            "preferred_types": ["Internship"],
            "preferred_mode": "Hybrid",
            "interests": ["Software Engineering"]
        }

        mock_opps = [
            {
                "id": "opp-low",
                "title": "Unrelated Opportunity",
                "organization": "Firm A",
                "type": "Scholarship",
                "skills": ["Solidity", "Rust"],
                "eligible_branches": ["Mechanical Engineering"],  # Ineligible branch
                "eligible_years": ["1st Year"],                   # Ineligible year
                "min_cgpa": 8.5,                                  # Ineligible CGPA
                "location": "Remote",
                "deadline": "2026-10-30"
            },
            {
                "id": "opp-high",
                "title": "Perfect Match SWE Intern",
                "organization": "Tech Corp",
                "type": "Internship",
                "skills": ["Python", "Data Structures", "Algorithms", "C++"], # 100% skill match
                "eligible_branches": ["Computer Science"],
                "eligible_years": ["3rd Year"],
                "min_cgpa": 7.0,
                "location": "Hybrid",
                "deadline": "2026-10-15"
            }
        ]

        ranked = evaluate_opportunities(student, mock_opps, reference_date=date(2026, 10, 4))
        
        # Verify perfect match ranks first
        self.assertEqual(ranked[0]["id"], "opp-high")
        self.assertTrue(ranked[0]["is_eligible"])
        self.assertEqual(ranked[0]["match_percentage"], 100.0)
        self.assertGreater(ranked[0]["relevance_score"], ranked[1]["relevance_score"])
        
        # Verify low match is marked ineligible
        self.assertEqual(ranked[1]["id"], "opp-low")
        self.assertFalse(ranked[1]["is_eligible"])

    # Explainability Test
    def test_explainability_data_structure(self):
        student = {
            "year": "2nd Year",
            "branch": "Information Technology",
            "cgpa": 8.2,
            "skills": ["Python", "Git"]
        }
        opp = {
            "title": "Open Source Sprint",
            "type": "Hackathon",
            "skills": ["Python", "Git", "Docker"],
            "eligible_branches": ["Information Technology"],
            "eligible_years": ["2nd Year"],
            "min_cgpa": 7.0
        }

        eval_res = evaluate_opportunities(student, [opp])[0]
        expl = eval_res["explanation"]

        self.assertIn("formula", expl)
        self.assertIn("calculation_steps", expl)
        self.assertEqual(len(expl["calculation_steps"]), 3)
        self.assertIn("summary", expl)
        self.assertEqual(eval_res["matched_skills"], ["Python", "Git"])
        self.assertEqual(eval_res["missing_skills"], ["Docker"])
        self.assertEqual(eval_res["match_percentage"], 66.7)


if __name__ == "__main__":
    unittest.main()
