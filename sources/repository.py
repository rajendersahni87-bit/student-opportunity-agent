"""
Opportunity Repository & Source Aggregator.
Coordinates multiple sources, gracefully handles live source failures,
and guarantees automatic fallback to the local JSON dataset.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import os

from .base import BaseOpportunitySource, sanitize_opportunity
from .json_source import JsonOpportunitySource
from .live_source import LiveApiOpportunitySource

logger = logging.getLogger(__name__)


class OpportunityRepository:
    """
    Central repository for discovering opportunities across multiple sources.
    Enforces high-availability: if any live source fails, the application
    seamlessly falls back to the reliable local JSON dataset.
    """

    def __init__(self, fallback_source: Optional[BaseOpportunitySource] = None):
        self.fallback_source = fallback_source or JsonOpportunitySource()
        self.sources: List[BaseOpportunitySource] = []

    def register_source(self, source: BaseOpportunitySource) -> None:
        """Register a new live or secondary opportunity source."""
        self.sources.append(source)

    def get_opportunities(
        self,
        category: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetches and aggregates opportunities across all registered sources.
        
        Returns:
            Tuple of:
            - List of sanitized, deduplicated opportunities
            - Metadata report detailing source statuses and any fallback activations
        """
        aggregated: Dict[str, Dict[str, Any]] = {}
        status_report = {
            "sources_attempted": [],
            "sources_succeeded": [],
            "sources_failed": [],
            "fallback_used": False,
            "total_loaded": 0,
            "errors": {}
        }

        live_data_found = False

        # 1. Attempt live / primary sources
        for src in self.sources:
            status_report["sources_attempted"].append(src.name)
            try:
                items = src.fetch_opportunities(category=category)
                for raw in items:
                    # Re-sanitize every item so custom sources can never inject malformed records
                    item = sanitize_opportunity(raw, default_source=src.name)
                    if item and item["id"] not in aggregated:
                        aggregated[item["id"]] = item
                status_report["sources_succeeded"].append(src.name)
                if items:
                    live_data_found = True
            except Exception as err:
                logger.warning(f"Source '{src.name}' failed. Activating fallback. Reason: {err}")
                status_report["sources_failed"].append(src.name)
                status_report["errors"][src.name] = str(err)

        # 2. Always incorporate or fall back to local JSON dataset
        # If no sources registered, or any live source failed, or we need the baseline dataset
        try:
            status_report["sources_attempted"].append(self.fallback_source.name)
            fallback_items = self.fallback_source.fetch_opportunities(category=category)
            
            # If live sources failed or returned empty, we mark fallback as actively used
            if not live_data_found or status_report["sources_failed"]:
                status_report["fallback_used"] = True

            # Merge fallback items (existing keys preserved if live had them, or populate baseline)
            for raw in fallback_items:
                item = sanitize_opportunity(raw, default_source=self.fallback_source.name)
                if item and item["id"] not in aggregated:
                    aggregated[item["id"]] = item

            status_report["sources_succeeded"].append(self.fallback_source.name)

        except Exception as fb_err:
            logger.critical(f"Critical error loading fallback source: {fb_err}")
            status_report["sources_failed"].append(self.fallback_source.name)
            status_report["errors"][self.fallback_source.name] = str(fb_err)

        results = list(aggregated.values())
        status_report["total_loaded"] = len(results)

        return results, status_report


# Singleton repository instance for application-wide access
_default_repository: Optional[OpportunityRepository] = None


def get_opportunity_repository() -> OpportunityRepository:
    """Returns or initializes the singleton OpportunityRepository."""
    global _default_repository
    if _default_repository is None:
        repo = OpportunityRepository()
        # Register a live source adapter (in standby / ready state)
        # Demonstrates how future live partner APIs plug in
        live_adapter = LiveApiOpportunitySource(
            name="External Partner Opportunity Feed (Standby)",
            endpoint_url=os.environ.get("OPPORTUNITY_API_URL") or None,
            simulate_failure=False
        )
        repo.register_source(live_adapter)
        _default_repository = repo
    return _default_repository
