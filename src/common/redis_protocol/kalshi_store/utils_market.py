"""Market metadata utilities split from kalshi_store.utils."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import orjson

from .reader_helpers.orderbook_parser import extract_orderbook_sizes
from .utils_coercion import logger

__all__ = [
    "normalise_trade_timestamp",
    "_normalise_trade_timestamp",
    "_normalise_timestamp_string",
    "_normalise_timestamp_numeric",
    "_parse_market_metadata",
    "_resolve_market_strike",
    "_coerce_strike_bounds",
    "_resolve_strike_from_bounds",
    "_extract_orderbook_sizes",
]

# Constants for timestamp detection
# Thresholds based on year 2200 to distinguish timestamp units:
# - Year 2200 ≈ 7.3e9 seconds
# - Year 2200 ≈ 7.3e12 milliseconds
# - Year 2200 ≈ 7.3e15 microseconds
# - Year 2200 ≈ 7.3e18 nanoseconds
_CONST_1_000_000_000 = 1_000_000_000
_CONST_1_000_000_000_000 = 1_000_000_000_000
_CONST_1_000_000_000_000_000 = 1_000_000_000_000_000
_CONST_10_000_000_000 = 10_000_000_000  # 10 billion - threshold for milliseconds
_CONST_10_000_000_000_000 = 10_000_000_000_000  # 10 trillion - threshold for microseconds


def _normalise_trade_timestamp(value: Any) -> str:
    """
    Convert Kalshi trade timestamps to ISO8601.

    Args:
        value: Timestamp value (string, int, or float)

    Returns:
        ISO8601 formatted timestamp or empty string if invalid
    """
    try:
        if isinstance(value, str):
            return _normalise_timestamp_string(value)
        if isinstance(value, (int, float)):
            return _normalise_timestamp_numeric(float(value))
    except (ValueError, TypeError, OSError):
        return ""
    return ""


def _normalise_timestamp_string(raw_value: str) -> str:
    candidate = raw_value[:-1] + "+00:00" if raw_value.endswith("Z") else raw_value
    dt = datetime.fromisoformat(candidate)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _normalise_timestamp_numeric(seconds: float) -> str:
    """Normalize numeric timestamps by detecting the unit based on magnitude."""
    if seconds > _CONST_1_000_000_000_000_000:  # > 10^15: nanoseconds
        seconds /= 1_000_000_000
    elif seconds > _CONST_10_000_000_000_000:  # > 10^13: microseconds
        seconds /= 1_000_000
    elif seconds > _CONST_10_000_000_000:  # > 10^10: milliseconds
        seconds /= 1_000
    # Otherwise treat as Unix seconds
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return dt.isoformat()


def normalise_trade_timestamp(value: Any) -> str:
    """
    Public wrapper for Kalshi trade timestamp normalization.
    """
    return _normalise_trade_timestamp(value)


def _parse_market_metadata(market_ticker: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse metadata JSON from Redis market data.

    Args:
        market_ticker: Market ticker for logging
        market_data: Market data dictionary

    Returns:
        Parsed metadata dictionary or None if missing/invalid
    """
    metadata_blob = market_data.get("metadata") if market_data else None
    if metadata_blob is None:
        return None
    try:
        return orjson.loads(metadata_blob)
    except orjson.JSONDecodeError:
        logger.warning("Invalid metadata JSON for market %s", market_ticker)
        return None


def _resolve_market_strike(metadata: Dict[str, Any]) -> Optional[float]:
    """
    Calculate strike from floor/cap/strike_type metadata.

    Delegates to common.strike_helpers.resolve_strike_from_metadata.

    Args:
        metadata: Market metadata dictionary

    Returns:
        Calculated strike value or None if cannot be determined
    """
    from common.strike_helpers import resolve_strike_from_metadata

    return resolve_strike_from_metadata(metadata)


def _coerce_strike_bounds(floor_strike: Any, cap_strike: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse floor and cap strike bounds.

    Delegates to common.strike_helpers.parse_strike_bounds.

    Args:
        floor_strike: Raw floor strike value
        cap_strike: Raw cap strike value

    Returns:
        Tuple of (floor_value, cap_value)
    """
    from common.strike_helpers import parse_strike_bounds

    floor_value, cap_value = parse_strike_bounds(floor_strike, cap_strike)

    def _is_invalid_input(raw_value: Any, parsed_value: Optional[float]) -> bool:
        return raw_value not in (None, "", b"") and parsed_value is None

    if _is_invalid_input(floor_strike, floor_value) or _is_invalid_input(cap_strike, cap_value):
        return None, None

    return floor_value, cap_value


def _resolve_strike_from_bounds(strike_type: str, floor_value: Optional[float], cap_value: Optional[float]) -> Optional[float]:
    """
    Calculate representative strike from bounds.

    Delegates to common.strike_helpers.calculate_strike_value.

    Args:
        strike_type: Type of strike
        floor_value: Floor strike value
        cap_value: Cap strike value

    Returns:
        Calculated strike or None
    """
    from common.strike_helpers import calculate_strike_value

    return calculate_strike_value(strike_type, floor_value, cap_value)


def _extract_orderbook_sizes(market_ticker: str, market_data: Dict[str, Any]) -> tuple[float, float]:
    """Delegate to canonical orderbook size extractor."""
    return extract_orderbook_sizes(market_ticker, market_data)


__all__ = [
    "_extract_orderbook_sizes",
    "_normalise_trade_timestamp",
    "_parse_market_metadata",
    "_resolve_market_strike",
]
