"""Type definitions for market matching."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MatchCandidate:
    """A normalized market candidate for matching."""

    market_id: str
    title: str
    description: str
    expiry: datetime
    floor_strike: float | None
    cap_strike: float | None
    source: str


@dataclass(frozen=True)
class MarketMatch:
    """A matched pair of markets from different platforms."""

    kalshi_market_id: str
    poly_market_id: str
    title_similarity: float
    expiry_delta_hours: float
    strike_match: bool


__all__ = [
    "MarketMatch",
    "MatchCandidate",
]
