"""
Modular Opportunity Sources Package.
Exports base interface, concrete sources, and repository aggregator.
"""

from .base import BaseOpportunitySource, sanitize_opportunity
from .json_source import JsonOpportunitySource
from .live_source import LiveApiOpportunitySource
from .repository import OpportunityRepository, get_opportunity_repository

__all__ = [
    "BaseOpportunitySource",
    "sanitize_opportunity",
    "JsonOpportunitySource",
    "LiveApiOpportunitySource",
    "OpportunityRepository",
    "get_opportunity_repository"
]
