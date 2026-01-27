"""Data models for LLM-based market extraction."""

from __future__ import annotations

from dataclasses import dataclass

VALID_POLY_STRIKE_TYPES = frozenset({"greater", "less", "between"})


@dataclass(frozen=True)
class MarketExtraction:
    """Extraction result for cross-platform matching.

    Fields:
        market_id: Unique identifier for the market.
        platform: "kalshi" or "poly".
        category: Market category (from Kalshi API for kalshi, LLM for poly).
        underlying: Asset/entity code (LLM-extracted for both platforms).
        strike_type: Type of strike condition (greater, less, between).
        floor_strike: Lower bound threshold, or None.
        cap_strike: Upper bound threshold, or None.
        close_time: ISO datetime string for market expiry.
    """

    market_id: str
    platform: str
    category: str
    underlying: str
    strike_type: str | None = None
    floor_strike: float | None = None
    cap_strike: float | None = None
    close_time: str | None = None


__all__ = ["MarketExtraction", "VALID_POLY_STRIKE_TYPES"]
