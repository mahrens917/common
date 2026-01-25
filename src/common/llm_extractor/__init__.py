"""Unified LLM-based market extraction service.

Exports:
    MarketExtraction: Unified extraction result dataclass.
    MarketExtractor: Batch extraction service with Redis caching.
    KALSHI_CATEGORIES: Valid category tuple for market classification.
"""

from .extractor import MarketExtractor
from .models import KALSHI_CATEGORIES, MarketExtraction

__all__ = ["KALSHI_CATEGORIES", "MarketExtraction", "MarketExtractor"]
