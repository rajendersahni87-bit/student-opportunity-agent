"""
Local JSON Dataset Opportunity Source (Reliable Fallback).
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from .base import BaseOpportunitySource, sanitize_opportunity, matches_category

logger = logging.getLogger(__name__)


class JsonOpportunitySource(BaseOpportunitySource):
    """
    Loads opportunities from local opportunities.json file.
    Serves as the high-availability baseline and fallback.
    """

    def __init__(self, file_path: Optional[Path] = None):
        super().__init__(name="Local JSON Storage", is_live=False)
        if file_path is None:
            # Default to data/opportunities.json relative to project root
            self.file_path = Path(__file__).resolve().parent.parent.parent / "data" / "opportunities.json"
        else:
            self.file_path = Path(file_path)

    def fetch_opportunities(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Reads and returns validated opportunities from disk."""
        if not self.file_path.exists():
            # Raise (not silently return []) so the repository can report the failure in its status
            raise FileNotFoundError(f"Opportunities file not found: {self.file_path}")

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            if not isinstance(raw_data, list):
                raise ValueError("JSON dataset is not a list")

            results = []
            for item in raw_data:
                sanitized = sanitize_opportunity(item, default_source="Local JSON File")
                if not sanitized:
                    continue

                # Filter by category if specified
                if not matches_category(sanitized.get("type"), category):
                    continue

                results.append(sanitized)

            return results

        except Exception as e:
            logger.exception(f"Error loading JSON opportunity source: {e}")
            raise

    def health_check(self) -> bool:
        return self.file_path.exists()
