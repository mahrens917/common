"""Converters for creating MatchCandidates from platform-specific market types."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .types import MatchCandidate

logger = logging.getLogger(__name__)


def _try_parse_float(value_str: str) -> float | None:
    """Parse string to float, returning None if invalid."""
    stripped = value_str.strip()
    if not stripped:
        return None
    # Check for valid float format: optional sign, digits, optional decimal
    clean = stripped.lstrip("+-")
    if not clean:
        return None
    parts = clean.split(".", 1)
    if not all(part.isdigit() for part in parts if part):
        return None
    return float(stripped)


if TYPE_CHECKING:
    from common.kalshi_catalog.types import DiscoveredMarket


def _parse_iso_datetime(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp string to datetime."""
    normalized = timestamp_str.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


_PATTERNS_ABOVE = [
    r"(?:above|over|greater than|>=?)\s*\$?([\d,]+\.?\d*)",
    r"\$?([\d,]+\.?\d*)\s*(?:or more|\+)",
]
_PATTERNS_BELOW = [
    r"(?:below|under|less than|<=?)\s*\$?([\d,]+\.?\d*)",
    r"\$?([\d,]+\.?\d*)\s*(?:or less|-)",
]


def _extract_strike_from_outcome(outcome: str, patterns: list[str]) -> float | None:
    """Extract a strike value from an outcome string using the given patterns."""
    for pattern in patterns:
        match = re.search(pattern, outcome, re.IGNORECASE)
        if match:
            raw_value = match.group(1).replace(",", "")
            parsed = _try_parse_float(raw_value)
            if parsed is not None:
                return parsed
    return None


def _extract_poly_strike_from_tokens(tokens: list[Any]) -> tuple[float | None, float | None]:
    """Extract floor/cap strike from poly token outcomes."""
    if not tokens:
        return None, None

    floor_strike: float | None = None
    cap_strike: float | None = None

    for token in tokens:
        outcome = getattr(token, "outcome", str(token))
        if not isinstance(outcome, str):
            continue

        above_val = _extract_strike_from_outcome(outcome, _PATTERNS_ABOVE)
        if above_val is not None:
            floor_strike = above_val

        below_val = _extract_strike_from_outcome(outcome, _PATTERNS_BELOW)
        if below_val is not None:
            cap_strike = below_val

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
    if hasattr(market, "tokens"):
        floor_strike, cap_strike = _extract_poly_strike_from_tokens(market.tokens)
    else:
        floor_strike, cap_strike = None, None

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
