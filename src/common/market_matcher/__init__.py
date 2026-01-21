"""Market matcher module for cross-platform event matching."""

from .converters import kalshi_market_to_candidate, poly_market_to_candidate
from .embedding_service import EmbeddingService
from .matcher import MarketMatcher
from .types import MarketMatch, MatchCandidate

__all__ = [
    "EmbeddingService",
    "MarketMatch",
    "MarketMatcher",
    "MatchCandidate",
    "kalshi_market_to_candidate",
    "poly_market_to_candidate",
]
