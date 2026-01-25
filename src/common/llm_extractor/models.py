"""Data models for LLM-based market extraction."""

from __future__ import annotations

from dataclasses import dataclass, field

KALSHI_CATEGORIES = (
    "Crypto",
    "Climate and Weather",
    "Economics",
    "Politics",
    "Sports",
    "Entertainment",
    "Science",
    "Technology",
    "Finance",
    "Company",
)


@dataclass(frozen=True)
class MarketExtraction:
    """Unified extraction result for a single market.

    All fields are LLM-generated and serve poly matching, logical consistency, and union bounds.
    """

    market_id: str
    platform: str
    category: str
    underlying: str
    subject: str
    entity: str
    scope: str
    floor_strike: float | None = None
    cap_strike: float | None = None
    parent_entity: str | None = None
    parent_scope: str | None = None
    is_conjunction: bool = False
    conjunction_scopes: tuple[str, ...] = field(default_factory=tuple)
    is_union: bool = False
    union_scopes: tuple[str, ...] = field(default_factory=tuple)


__all__ = ["KALSHI_CATEGORIES", "MarketExtraction"]
