"""Filtering utilities for Kalshi market catalog discovery."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from common.time_helpers.expiry_conversions import parse_expiry_datetime
from common.truthy import pick_if

from .types import DiscoveredMarket

logger = logging.getLogger(__name__)

# Sentinel for markets without valid strike - sorts last
_NO_STRIKE_SENTINEL = float("inf")

SUPPORTED_STRIKE_TYPES = frozenset(
    {
        "greater",
        "greater_or_equal",
        "less",
        "less_or_equal",
        "between",
        "custom",
        "functional",
        "structured",
    }
)

_UNKNOWN_FIELD = "unknown"


def _extract_string_field(data: Dict[str, Any], key: str) -> str:
    """Extract a string field from a dict, returning 'unknown' if not present."""
    value = data.get(key)
    if value is not None:
        return str(value)
    return _UNKNOWN_FIELD


@dataclass
class SkippedMarketStats:
    """Statistics about markets skipped during filtering."""

    by_strike_type: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    by_category: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_zero_volume: int = 0

    @property
    def total_skipped(self) -> int:
        """Total number of skipped markets."""
        return sum(len(tickers) for tickers in self.by_strike_type.values()) + self.by_zero_volume

    def add_skipped(self, ticker: str, strike_type: str, category: str) -> None:
        """Record a skipped market."""
        self.by_strike_type[strike_type].append(ticker)
        self.by_category[category] += 1

    def add_zero_volume(self) -> None:
        """Record a market skipped due to zero volume."""
        self.by_zero_volume += 1


def is_expiring_within_window(close_time_str: str, expiry_window_seconds: int) -> bool:
    """Check if a market closes within the configured expiry window.

    Args:
        close_time_str: ISO format close time string
        expiry_window_seconds: Maximum seconds from now for expiry (0 or negative means no limit)

    Returns:
        True if market closes within window (or any future market if no limit), False otherwise
    """
    if not close_time_str:
        return False
    try:
        close_time = parse_expiry_datetime(close_time_str)
    except (ValueError, TypeError):  # policy_guard: allow-silent-handler
        return False
    now = datetime.now(timezone.utc)
    delta = (close_time - now).total_seconds()
    if expiry_window_seconds <= 0:
        return delta > 0
    return 0 < delta <= expiry_window_seconds


def group_markets_by_event(
    markets: List[Dict[str, Any]],
    expiry_window_seconds: int,
) -> Dict[str, List[Dict[str, Any]]]:
    """Group markets by their event_ticker, filtering for the expiry window.

    Args:
        markets: List of market dictionaries
        expiry_window_seconds: Maximum seconds from now for expiry

    Returns:
        Dict mapping event_ticker to list of markets
    """
    event_markets: Dict[str, List[Dict[str, Any]]] = {}

    for market in markets:
        event_ticker = market.get("event_ticker")
        close_time = market.get("close_time")

        if not event_ticker or not close_time:
            continue

        if not is_expiring_within_window(close_time, expiry_window_seconds):
            continue

        if event_ticker not in event_markets:
            event_markets[event_ticker] = []
        event_markets[event_ticker].append(market)

    return event_markets


def _get_strike_type(market: Dict[str, Any]) -> str:
    """Get strike type from market, normalized to lowercase."""
    strike_type = market.get("strike_type")
    if not isinstance(strike_type, str):
        return "missing"
    return strike_type.lower()


def _has_supported_strike_type(market: Dict[str, Any]) -> bool:
    """Check if market has a supported strike type."""
    return _get_strike_type(market) in SUPPORTED_STRIKE_TYPES


def _is_valid_market_in_window(market: Any, expiry_window_seconds: int) -> bool:
    """Check if item is a dict with a close_time string within the expiry window."""
    if not isinstance(market, dict):
        return False
    close_time = market.get("close_time")
    if not isinstance(close_time, str):
        return False
    return is_expiring_within_window(close_time, expiry_window_seconds)


def _record_unsupported_strike(
    market: Dict[str, Any],
    skipped_stats: SkippedMarketStats | None,
) -> None:
    """Log and record a market skipped for unsupported strike type."""
    ticker = _extract_string_field(market, "ticker")
    strike_type = _get_strike_type(market)
    category = _extract_string_field(market, "category")
    logger.info(
        "Skipping market %s: unsupported strike_type '%s' (category=%s)",
        ticker,
        strike_type,
        category,
    )
    if skipped_stats is not None:
        skipped_stats.add_skipped(ticker, strike_type, category)


def _record_zero_volume(
    market: Dict[str, Any],
    skipped_stats: SkippedMarketStats | None,
) -> None:
    """Log and record a market skipped for zero volume."""
    ticker = _extract_string_field(market, "ticker")
    logger.info("Skipping market %s: zero volume", ticker)
    if skipped_stats is not None:
        skipped_stats.add_zero_volume()


def filter_markets_for_window(
    nested_markets: Any,
    expiry_window_seconds: int,
    skipped_stats: SkippedMarketStats | None = None,
) -> List[Dict[str, Any]]:
    """Filter nested markets to only those expiring within the window.

    Args:
        nested_markets: List of market dictionaries from event details
        expiry_window_seconds: Maximum seconds from now for expiry
        skipped_stats: Optional stats collector for skipped markets

    Returns:
        List of markets within the expiry window with supported strike types
    """
    if not isinstance(nested_markets, list):
        return []
    markets_in_window: List[Dict[str, Any]] = []
    for market in nested_markets:
        if not _is_valid_market_in_window(market, expiry_window_seconds):
            continue
        if not _has_supported_strike_type(market):
            _record_unsupported_strike(market, skipped_stats)
            continue
        volume = market.get("volume")
        if isinstance(volume, int) and volume == 0:
            _record_zero_volume(market, skipped_stats)
            continue
        markets_in_window.append(market)
    return markets_in_window


def convert_to_discovered_market(market: Dict[str, Any]) -> DiscoveredMarket:
    """Convert raw market dict to DiscoveredMarket dataclass.

    Args:
        market: Raw market dictionary from API

    Returns:
        DiscoveredMarket instance
    """
    ticker_value = market.get("ticker")
    ticker = pick_if(ticker_value is not None, lambda: str(ticker_value), lambda: "")
    close_time_value = market.get("close_time")
    close_time = pick_if(close_time_value is not None, lambda: str(close_time_value), lambda: "")
    subtitle_value = market.get("subtitle")
    subtitle = pick_if(subtitle_value is not None, lambda: str(subtitle_value), lambda: "")
    return DiscoveredMarket(
        ticker=ticker,
        close_time=close_time,
        subtitle=subtitle,
        cap_strike=market.get("cap_strike"),
        floor_strike=market.get("floor_strike"),
        raw_data=market,
    )


def _get_valid_strike(value: float | None) -> float | None:
    """Return value if it's valid (non-None and non-zero), else None."""
    if value is not None and value != 0:
        return value
    return None


def compute_effective_strike(market: DiscoveredMarket) -> float:
    """Compute effective strike for sorting markets.

    If both cap_strike and floor_strike are non-zero, average them.
    Otherwise use whichever is non-zero.
    Returns inf if neither is set or both are zero (sorts last).
    """
    cap = _get_valid_strike(market.cap_strike)
    floor = _get_valid_strike(market.floor_strike)

    if cap is not None and floor is not None:
        return (cap + floor) / 2
    return cap if cap is not None else (floor if floor is not None else _NO_STRIKE_SENTINEL)


def sort_markets_by_strike(markets: List[DiscoveredMarket]) -> List[DiscoveredMarket]:
    """Sort markets by effective strike value ascending.

    Markets without valid strikes are placed at the end.

    Args:
        markets: List of discovered markets to sort

    Returns:
        New list sorted by effective strike
    """
    return sorted(markets, key=compute_effective_strike)


__all__ = [
    "SkippedMarketStats",
    "compute_effective_strike",
    "convert_to_discovered_market",
    "filter_markets_for_window",
    "group_markets_by_event",
    "is_expiring_within_window",
    "sort_markets_by_strike",
]
