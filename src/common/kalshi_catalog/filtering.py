"""Filtering utilities for Kalshi market catalog discovery."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from common.time_helpers.expiry_conversions import parse_expiry_datetime
from common.truthy import pick_if

from .types import DiscoveredMarket, StrikeValidationError

logger = logging.getLogger(__name__)


def is_expiring_within_window(close_time_str: str, expiry_window_seconds: int) -> bool:
    """Check if a market closes within the configured expiry window.

    Args:
        close_time_str: ISO format close time string
        expiry_window_seconds: Maximum seconds from now for expiry

    Returns:
        True if market closes within window, False otherwise
    """
    if not close_time_str:
        return False
    try:
        close_time = parse_expiry_datetime(close_time_str)
    except (ValueError, TypeError):  # policy_guard: allow-silent-handler
        return False
    now = datetime.now(timezone.utc)
    delta = (close_time - now).total_seconds()
    return 0 < delta <= expiry_window_seconds


def validate_strikes(market: Dict[str, Any]) -> bool:
    """Validate that market has valid strike configuration.

    A market has valid strikes if:
    - At least one of cap_strike or floor_strike is present
    - If both are present, they must be different

    Args:
        market: Market dictionary

    Returns:
        True if strikes are valid, False otherwise

    Raises:
        StrikeValidationError: If validation fails with details
    """
    cap_strike = market.get("cap_strike")
    floor_strike = market.get("floor_strike")

    if cap_strike is None and floor_strike is None:
        raise StrikeValidationError(f"Market {market.get('ticker')} missing both cap_strike and floor_strike")
    if cap_strike is not None and floor_strike is not None and cap_strike == floor_strike:
        raise StrikeValidationError(f"Market {market.get('ticker')} has equal cap_strike and floor_strike: {cap_strike}")
    return True


def has_valid_strikes(market: Dict[str, Any]) -> bool:
    """Check if market has valid strike configuration (non-raising version).

    Args:
        market: Market dictionary

    Returns:
        True if strikes are valid, False otherwise
    """
    try:
        return validate_strikes(market)
    except StrikeValidationError:  # policy_guard: allow-silent-handler
        return False


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


def filter_mutually_exclusive_events(
    events: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Filter to only mutually exclusive events.

    Args:
        events: Dict mapping event_ticker to event details

    Returns:
        Dict containing only mutually exclusive events
    """
    return {ticker: details for ticker, details in events.items() if details.get("mutually_exclusive") is True}


def filter_markets_for_window(
    nested_markets: Any,
    expiry_window_seconds: int,
) -> List[Dict[str, Any]]:
    """Filter nested markets to only those expiring within the window.

    Args:
        nested_markets: List of market dictionaries from event details
        expiry_window_seconds: Maximum seconds from now for expiry

    Returns:
        List of markets within the expiry window
    """
    if not isinstance(nested_markets, list):
        return []
    markets_in_window: List[Dict[str, Any]] = []
    for market in nested_markets:
        if not isinstance(market, dict):
            continue
        close_time = market.get("close_time")
        if isinstance(close_time, str) and is_expiring_within_window(close_time, expiry_window_seconds):
            markets_in_window.append(market)
    return markets_in_window


def filter_markets_with_valid_strikes(
    markets: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Filter markets to only those with valid strike configuration.

    Args:
        markets: List of market dictionaries

    Returns:
        List of markets with valid strikes
    """
    valid_markets: List[Dict[str, Any]] = []
    for market in markets:
        if has_valid_strikes(market):
            valid_markets.append(market)
        else:
            logger.debug(
                "Skipping market %s: invalid strikes (cap=%s, floor=%s)",
                market.get("ticker"),
                market.get("cap_strike"),
                market.get("floor_strike"),
            )
    return valid_markets


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
    return DiscoveredMarket(
        ticker=ticker,
        close_time=close_time,
        cap_strike=market.get("cap_strike"),
        floor_strike=market.get("floor_strike"),
        raw_data=market,
    )


__all__ = [
    "convert_to_discovered_market",
    "filter_markets_for_window",
    "filter_markets_with_valid_strikes",
    "filter_mutually_exclusive_events",
    "group_markets_by_event",
    "has_valid_strikes",
    "is_expiring_within_window",
    "validate_strikes",
]
