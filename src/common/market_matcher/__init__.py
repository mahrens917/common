"""Market matcher module for cross-platform event matching."""

from .converters import kalshi_market_to_candidate, poly_market_to_candidate
from .embedding_service import EmbeddingService, clear_old_embedding_cache
from .field_extractor import KALSHI_CATEGORIES, ExtractedFields, FieldExtractor
from .matcher import MarketMatcher
from .types import MarketMatch, MatchCandidate

__all__ = [
    "EmbeddingService",
    "ExtractedFields",
    "FieldExtractor",
    "KALSHI_CATEGORIES",
    "MarketMatch",
    "MarketMatcher",
    "MatchCandidate",
    "clear_old_embedding_cache",
    "kalshi_market_to_candidate",
    "poly_market_to_candidate",
]
