"""
Unit Tests for Modular Opportunity Source Layer.
Verifies base interfaces, JSON fallback, live failure resilience, and category filtering.
"""

import unittest
from pathlib import Path
from engine.sources import (
    BaseOpportunitySource,
    JsonOpportunitySource,
    LiveApiOpportunitySource,
    OpportunityRepository,
    sanitize_opportunity
)


class TestModularOpportunitySources(unittest.TestCase):

    def setUp(self):
        self.json_source = JsonOpportunitySource()

    def test_json_fallback_source_loads_data(self):
        """Verifies that the local JSON source successfully loads the 40 opportunities."""
        items = self.json_source.fetch_opportunities()
        self.assertGreaterEqual(len(items), 40)
        self.assertIn("title", items[0])
        self.assertIn("skills", items[0])

    def test_category_filtering(self):
        """Verifies category filtering across internships, hackathons, coding competitions, scholarships."""
        internships = self.json_source.fetch_opportunities(category="internships")
        self.assertTrue(len(internships) > 0)
        for item in internships:
            self.assertEqual(item["type"].lower(), "internship")

        hackathons = self.json_source.fetch_opportunities(category="hackathons")
        self.assertTrue(len(hackathons) > 0)
        for item in hackathons:
            self.assertEqual(item["type"].lower(), "hackathon")

        competitions = self.json_source.fetch_opportunities(category="coding competitions")
        self.assertTrue(len(competitions) > 0)
        for item in competitions:
            self.assertEqual(item["type"].lower(), "coding competition")

        scholarships = self.json_source.fetch_opportunities(category="scholarships")
        self.assertTrue(len(scholarships) > 0)
        for item in scholarships:
            self.assertEqual(item["type"].lower(), "scholarship")

    def test_live_source_failure_graceful_fallback(self):
        """
        CRITICAL TEST: If a live source fails with an exception,
        the repository MUST NOT crash and MUST continue using the local JSON dataset.
        """
        repo = OpportunityRepository(fallback_source=self.json_source)

        # Register a live source configured to throw ConnectionError
        failing_live_source = LiveApiOpportunitySource(
            name="Failing Third-Party API",
            endpoint_url="https://api.example.com/opportunities",
            simulate_failure=True
        )
        repo.register_source(failing_live_source)

        # Execute fetch
        items, status = repo.get_opportunities()

        # Verify application did not crash and fallback was engaged
        self.assertGreaterEqual(len(items), 40)
        self.assertIn("Failing Third-Party API", status["sources_failed"])
        self.assertTrue(status["fallback_used"])
        self.assertIn("Failing Third-Party API", status["errors"])

    def test_live_and_fallback_merge(self):
        """Verifies that items from a functioning live source merge properly with the fallback."""
        repo = OpportunityRepository(fallback_source=self.json_source)

        class MockWorkingLiveSource(BaseOpportunitySource):
            def __init__(self):
                super().__init__(name="Mock Live Partner Feed", is_live=True)

            def fetch_opportunities(self, category=None):
                return [{
                    "id": "live-new-001",
                    "title": "Brand New Live AI Fellowship 2027",
                    "organization": "OpenAI / Partner",
                    "type": "Fellowship",
                    "skills": ["Python", "PyTorch"],
                    "eligible_branches": ["Computer Science"],
                    "eligible_years": ["3rd Year", "4th Year"],
                    "min_cgpa": 7.5,
                    "location": "Remote",
                    "deadline": "2026-12-31",
                    "application_url": "https://example.com/apply-live"
                }]

        repo.register_source(MockWorkingLiveSource())
        items, status = repo.get_opportunities()

        # Both the new live item and existing fallback items should be present
        ids = [item["id"] for item in items]
        self.assertIn("live-new-001", ids)
        self.assertIn("opp-001", ids)
        self.assertIn("Mock Live Partner Feed", status["sources_succeeded"])

    def test_sanitize_opportunity_drops_invalid(self):
        """Ensures corrupted live records without titles are safely rejected."""
        invalid_item = {"some_field": 123}  # No title
        self.assertIsNone(sanitize_opportunity(invalid_item))

        valid_item = {"title": "Quick Hackathon"}
        sanitized = sanitize_opportunity(valid_item)
        self.assertIsNotNone(sanitized)
        self.assertEqual(sanitized["title"], "Quick Hackathon")
        self.assertEqual(sanitized["type"], "Opportunity")


if __name__ == "__main__":
    unittest.main()
