"""
Unit Tests for AI Recommendation Layer (engine/agent.py).
Verifies the 5 required outputs and compliance with strict constraints.
"""

import unittest
from engine.matcher import evaluate_opportunities
from engine.agent import generate_offline_agent_insight, format_value_or_unknown


class TestAIRecommendationLayer(unittest.TestCase):

    def setUp(self):
        self.eligible_student = {
            "name": "Dev Sharma",
            "degree": "B.Tech",
            "year": "3rd Year",
            "branch": "Computer Science",
            "cgpa": 8.4,
            "skills": ["Python", "Data Structures", "Algorithms", "Git"],
            "interests": ["Software Engineering"],
            "preferred_types": ["Internship"],
            "preferred_mode": "Hybrid"
        }

        self.ineligible_student = {
            "name": "Ananya Roy",
            "degree": "B.Tech",
            "year": "1st Year",  # Ineligible for 3rd year internship
            "branch": "Mechanical Engineering", # Ineligible branch
            "cgpa": 6.2,
            "skills": ["Python"],
            "interests": ["Robotics"],
            "preferred_types": ["Internship"],
            "preferred_mode": "Hybrid"
        }

        self.target_opp = {
            "id": "test-opp-01",
            "title": "Google Summer SWE Intern",
            "organization": "Google",
            "type": "Internship",
            "skills": ["Python", "Data Structures", "Algorithms", "C++"],
            "eligible_branches": ["Computer Science", "Information Technology"],
            "eligible_years": ["2nd Year", "3rd Year"],
            "min_cgpa": 7.5,
            "location": "Bangalore, India",
            "deadline": "2026-10-20",
            "application_url": "https://careers.google.com/students/"
        }

    def test_five_required_outputs_present(self):
        evaluated = evaluate_opportunities(self.eligible_student, [self.target_opp])[0]
        insight = generate_offline_agent_insight(self.eligible_student, evaluated)

        # Verify all 5 required outputs are present and non-empty
        self.assertIn("why_recommended", insight)
        self.assertTrue(len(insight["why_recommended"]) > 0)

        self.assertIn("skill_alignment", insight)
        self.assertTrue(len(insight["skill_alignment"]) > 0)

        self.assertIn("eligibility_explanation", insight)
        self.assertTrue(len(insight["eligibility_explanation"]) > 0)

        self.assertIn("missing_skills", insight)
        self.assertTrue(len(insight["missing_skills"]) > 0)

        self.assertIn("recommended_next_actions", insight)
        self.assertIsInstance(insight["recommended_next_actions"], list)
        self.assertTrue(len(insight["recommended_next_actions"]) >= 3)

    def test_llm_cannot_override_eligibility_when_ineligible(self):
        evaluated = evaluate_opportunities(self.ineligible_student, [self.target_opp])[0]
        self.assertFalse(evaluated["is_eligible"])

        insight = generate_offline_agent_insight(self.ineligible_student, evaluated)
        
        # Verify ineligibility is strictly maintained and explained
        self.assertIn("INELIGIBLE", insight["eligibility_explanation"].upper())
        self.assertIn("Not Recommended", insight["why_recommended"])
        self.assertNotIn("VERIFIED ELIGIBLE", insight["eligibility_explanation"])

    def test_missing_information_reports_unknown(self):
        incomplete_student = {
            "name": "",
            "degree": None,
            "year": "2nd Year",
            "branch": "Computer Science",
            "cgpa": None,
            "skills": []
        }
        incomplete_opp = {
            "title": "Generic Coding Test",
            "organization": None,
            "type": "Coding Competition",
            "skills": [],
            "eligible_branches": [],
            "eligible_years": [],
            "min_cgpa": 0.0,
            "location": None,
            "deadline": None
        }

        self.assertEqual(format_value_or_unknown(incomplete_student["degree"]), "Unknown")
        self.assertEqual(format_value_or_unknown(incomplete_student["cgpa"]), "Unknown")
        self.assertEqual(format_value_or_unknown(incomplete_opp["location"]), "Unknown")

        evaluated = evaluate_opportunities(incomplete_student, [incomplete_opp])[0]
        insight = generate_offline_agent_insight(incomplete_student, evaluated)
        
        self.assertIsNotNone(insight)
        self.assertIn("why_recommended", insight)


if __name__ == "__main__":
    unittest.main()
