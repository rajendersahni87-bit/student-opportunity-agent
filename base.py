"""
Base Interfaces and Schema Sanitization for Modular Opportunity Sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import hashlib
import logging

logger = logging.getLogger(__name__)

# Required fields according to the standard opportunity schema
REQUIRED_FIELDS = [
    "id", "title", "organization", "type", "description",
    "skills", "eligible_branches", "eligible_years", "min_cgpa",
    "location", "deadline", "application_url"
]


def matches_category(item_type: str, category: Optional[str]) -> bool:
    """Shared category filter: case-insensitive, plural-tolerant, exact (no substring matching)."""
    if not category or not category.strip():
        return True
    norm = lambda v: str(v or "").strip().lower().rstrip("s")
    return norm(item_type) == norm(category)


def _safe_url(url: Any) -> str:
    """Only http(s) links are allowed; anything else (javascript:, data:, ...) becomes '#'."""
    url = str(url or "").strip()
    return url if url.lower().startswith(("https://", "http://")) else "#"


def sanitize_opportunity(data: Dict[str, Any], default_source: str = "Unknown") -> Optional[Dict[str, Any]]:
    """
    Validates and standardizes an opportunity payload from any source.
    Ensures required fields exist with valid defaults so external data never breaks the engine.
    """
    if not isinstance(data, dict):
        return None

    raw_title = data.get("title")
    title = "" if raw_title is None else str(raw_title).strip()
    if not title:
        return None  # Title is mandatory

    organization = str(data.get("organization") or "Various Organizations")
    # Stable across processes (built-in hash() is randomised per run, which broke selection/bookmarks)
    stable = hashlib.sha1(f"{title}|{organization}".lower().encode("utf-8")).hexdigest()[:8]
    opp_id = str(data.get("id") or f"opp-{stable}")
    opp_type = str(data.get("type") or "Opportunity").strip().title()
    description = str(data.get("description") or "No description provided.")
    
    # Skills normalization to list
    raw_skills = data.get("skills") or data.get("required_skills") or []
    if isinstance(raw_skills, str):
        skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
    elif isinstance(raw_skills, list):
        skills = [str(s).strip() for s in raw_skills if str(s).strip()]
    else:
        skills = []

    # Eligible branches
    raw_branches = data.get("eligible_branches") or data.get("allowed_branches") or ["All Engineering Branches"]
    if isinstance(raw_branches, str):
        eligible_branches = [b.strip() for b in raw_branches.split(",") if b.strip()]
    elif isinstance(raw_branches, list):
        eligible_branches = [str(b).strip() for b in raw_branches if str(b).strip()]
    else:
        eligible_branches = ["All Engineering Branches"]

    # Eligible years
    raw_years = data.get("eligible_years") or data.get("allowed_years") or ["All Years"]
    if isinstance(raw_years, str):
        eligible_years = [y.strip() for y in raw_years.split(",") if y.strip()]
    elif isinstance(raw_years, list):
        eligible_years = [str(y).strip() for y in raw_years if str(y).strip()]
    else:
        eligible_years = ["All Years"]

    # Min CGPA
    try:
        min_cgpa = float(data.get("min_cgpa", 0.0) or 0.0)
    except (ValueError, TypeError):
        min_cgpa = 0.0

    location = str(data.get("location") or "Remote / Online")
    deadline = str(data.get("deadline") or "")
    app_url = _safe_url(data.get("application_url") or data.get("apply_url"))

    raw_tags = data.get("domain_tags")
    domain_tags = [str(t).strip() for t in raw_tags if str(t).strip()] if isinstance(raw_tags, list) else list(skills[:4])

    return {
        "id": opp_id,
        "title": title,
        "organization": organization,
        "type": opp_type,
        "description": description,
        "skills": skills,
        "eligible_branches": eligible_branches,
        "eligible_years": eligible_years,
        "min_cgpa": min_cgpa,
        "location": location,
        "deadline": deadline,
        "application_url": app_url,
        "mode": str(data.get("mode") or "").strip(),
        "domain_tags": domain_tags,
        "is_demo": bool(data.get("is_demo", False)),
        "source_provider": data.get("source_provider", default_source),
        "stipend_or_prize": data.get("stipend_or_prize") or "Competitive / Recognition",
        "selection_process": data.get("selection_process") or "Standard Application Review"
    }


class BaseOpportunitySource(ABC):
    """
    Abstract Base Class for all opportunity data sources.
    Future sources (REST APIs, partner webhooks, RSS feeds, scrapers) implement this interface.
    """

    def __init__(self, name: str, is_live: bool = False):
        self.name = name
        self.is_live = is_live

    @abstractmethod
    def fetch_opportunities(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch opportunities from the underlying source.
        Raises an exception if the source is unavailable.
        """
        pass

    def health_check(self) -> bool:
        """Verify if source is reachable/operational."""
        return True
