"""
Live Opportunity Source Interface & API Adapter.
Demonstrates how future remote endpoints (REST APIs, partner feeds, aggregators)
plug into the system with failure-resilient adapters.
"""

from typing import Dict, List, Any, Optional
import urllib.request
import json
import logging

from .base import BaseOpportunitySource, sanitize_opportunity, matches_category

MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # refuse oversized payloads

logger = logging.getLogger(__name__)


class LiveApiOpportunitySource(BaseOpportunitySource):
    """
    Adapter for remote live opportunity APIs.
    Supports endpoints providing internships, hackathons, coding competitions, scholarships.
    Features configurable timeout and fault-injection for resilience testing.
    """

    def __init__(
        self,
        name: str = "Live Partner Opportunity API",
        endpoint_url: Optional[str] = None,
        timeout_seconds: float = 3.0,
        simulate_failure: bool = False
    ):
        super().__init__(name=name, is_live=True)
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.simulate_failure = simulate_failure

    def fetch_opportunities(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetches live opportunities from the remote endpoint.
        Raises an exception if the network call fails or timeout expires.
        """
        # Test hook for resilience verification
        if self.simulate_failure:
            raise ConnectionError(f"Simulated live network failure for '{self.name}'.")

        # If no real remote URL is configured, report empty (or simulate live stream)
        if not self.endpoint_url:
            return []

        if not str(self.endpoint_url).lower().startswith(("https://", "http://")):
            raise ValueError("Live source endpoint must be an http(s) URL")

        # Real HTTP GET request
        req = urllib.request.Request(
            self.endpoint_url,
            headers={"User-Agent": "StudentOpportunityAgent/1.0", "Accept": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise IOError(f"Remote API responded with status {response.status}")
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise IOError("Remote API response too large")
                payload = json.loads(body.decode("utf-8"))

            if isinstance(payload, dict):
                payload = payload.get("data", [])
            if not isinstance(payload, list):
                raise ValueError("Remote API returned an unexpected payload shape")
            raw_items = payload
            results = []
            for item in raw_items:
                sanitized = sanitize_opportunity(item, default_source=self.name)
                if not sanitized:
                    continue

                if not matches_category(sanitized.get("type"), category):
                    continue

                results.append(sanitized)

            return results

        except Exception as err:
            logger.warning(f"Live source '{self.name}' failed to fetch: {err}")
            raise err

    def health_check(self) -> bool:
        if self.simulate_failure:
            return False
        return True
