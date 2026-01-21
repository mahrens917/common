"""Converters for creating MatchCandidates from platform-specific market types."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .types import MatchCandidate

if TYPE_CHECKING:
    from common.kalshi_catalog.types import DiscoveredMarket


def _parse_iso_datetime(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp string to datetime."""
    normalized = timestamp_str.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _extract_poly_strike_from_tokens(tokens: list[Any]) -> tuple[float | None, float | None]:
    """Extract floor/cap strike from poly token outcomes.

    Attempts to parse numeric thresholds from token outcome strings.

    Returns:
        Tuple of (floor_strike, cap_strike).
    """
    if not tokens:
        return None, None

    patterns_above = [
        r"(?:above|over|greater than|>=?)\s*\$?([\d,]+\.?\d*)",
        r"\$?([\d,]+\.?\d*)\s*(?:or more|\+)",
    ]
    patterns_below = [
        r"(?:below|under|less than|<=?)\s*\$?([\d,]+\.?\d*)",
        r"\$?([\d,]+\.?\d*)\s*(?:or less|-)",
    ]

    floor_strike: float | None = None
    cap_strike: float | None = None

    for token in tokens:
        outcome = getattr(token, "outcome", str(token))
        if not isinstance(outcome, str):
            continue

        for pattern in patterns_above:
            match = re.search(pattern, outcome, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(",", ""))
                    floor_strike = value
                except ValueError:
                    continue

        for pattern in patterns_below:
            match = re.search(pattern, outcome, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(",", ""))
                    cap_strike = value
                except ValueError:
                    continue

    return floor_strike, cap_strike


def kalshi_market_to_candidate(market: DiscoveredMarket, event_title: str) -> MatchCandidate:
    """Convert a Kalshi DiscoveredMarket to a MatchCandidate.

    Args:
        market: The Kalshi discovered market.
        event_title: Title of the parent event.

    Returns:
        MatchCandidate for use in matching.
    """
    expiry = _parse_iso_datetime(market.close_time)

    return MatchCandidate(
        market_id=market.ticker,
        title=event_title,
        description=market.subtitle,
        expiry=expiry,
        floor_strike=market.floor_strike,
        cap_strike=market.cap_strike,
        source="kalshi",
    )


def poly_market_to_candidate(market: Any) -> MatchCandidate:
    """Convert a Polymarket Market to a MatchCandidate.

    Args:
        market: The Polymarket market object with title, description, end_date, tokens.

    Returns:
        MatchCandidate for use in matching.
    """
    tokens = getattr(market, "tokens", [])
    floor_strike, cap_strike = _extract_poly_strike_from_tokens(tokens)

    expiry = market.end_date
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    return MatchCandidate(
        market_id=market.condition_id,
        title=market.title,
        description=market.description,
        expiry=expiry,
        floor_strike=floor_strike,
        cap_strike=cap_strike,
        source="poly",
    )


__all__ = [
    "kalshi_market_to_candidate",
    "poly_market_to_candidate",
]
