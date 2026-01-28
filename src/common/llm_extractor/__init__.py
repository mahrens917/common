"""Unified LLM-based market extraction service.

Exports:
    MarketExtraction: Extraction result dataclass.
    VALID_POLY_STRIKE_TYPES: Valid strike types for Poly markets.
    KalshiUnderlyingExtractor: Extract underlyings from Kalshi markets.
    KalshiDedupExtractor: Deduplicate underlyings within categories.
    PolyExtractor: Extract fields from Poly markets with validation.
    ExpiryAligner: Align Poly/Kalshi expiries for near-miss pairs.
"""

from .extractor import ExpiryAligner, KalshiDedupExtractor, KalshiUnderlyingExtractor, PolyExtractor
from .models import VALID_POLY_STRIKE_TYPES, MarketExtraction

__all__ = [
    "ExpiryAligner",
    "KalshiDedupExtractor",
    "KalshiUnderlyingExtractor",
    "MarketExtraction",
    "PolyExtractor",
    "VALID_POLY_STRIKE_TYPES",
]
