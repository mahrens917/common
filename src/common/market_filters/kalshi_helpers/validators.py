"""Validation helpers for Kalshi markets (ticker, pricing, expiry)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Mapping, Optional, Tuple

from common.redis_schema import is_supported_kalshi_ticker

from ...time_helpers.expiry_conversions import parse_expiry_datetime
from .data_converters import decode_payload

logger = logging.getLogger(__name__)


# --- Ticker validation ---


def validate_ticker_support(
    metadata: Mapping[str, Any],
    checker: Callable[[str], bool] = is_supported_kalshi_ticker,
) -> tuple[bool, Optional[str]]:
    """Validate ticker is in supported category."""
    ticker_value = metadata.get("ticker") or metadata.get("market_ticker")
    if not ticker_value:
        return True, None  # No ticker to validate

    if not checker(str(ticker_value)):
        return False, "unsupported_category"

    return True, None


# --- Pricing validation ---


def check_side_validity(price: Optional[float], size: Optional[int]) -> bool:
    """Check if a bid/ask side has valid data."""
    return price is not None and price >= 0.0 and size is not None


def validate_pricing_data(
    bid_price: Optional[float],
    bid_size: Optional[int],
    ask_price: Optional[float],
    ask_size: Optional[int],
    require_pricing: bool,
) -> Tuple[bool, Optional[str]]:
    """Validate pricing data meets requirements.

    Returns: (is_valid, reason)
    """
    has_bid = check_side_validity(bid_price, bid_size)
    has_ask = check_side_validity(ask_price, ask_size)

    has_pricing = has_bid or has_ask

    if require_pricing and not has_pricing:
        return False, "missing_pricing_data"

    return True, None


# --- Expiry validation ---


def parse_expiry(metadata: Mapping[str, Any]) -> tuple[Optional[str], Optional[datetime]]:
    """Parse expiry from metadata, returning raw string and parsed datetime."""
    expiry_raw = decode_payload(metadata.get("close_time")) or decode_payload(metadata.get("expiry"))
    if not expiry_raw:
        return None, None

    try:
        expiry_dt = parse_expiry_datetime(str(expiry_raw))
        return str(expiry_raw), expiry_dt
    except ValueError as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Failed to parse expiry datetime: expiry=%r, error=%s", expiry_raw, exc)
        return str(expiry_raw), None


def validate_expiry(expiry_dt: Optional[datetime], current_time: datetime) -> tuple[bool, Optional[str]]:
    """Validate expiry is in the future."""
    if expiry_dt is None:
        _none_guard_value = False, "unparseable_expiry"
        return _none_guard_value

    if expiry_dt <= current_time:
        return False, "expired"

    return True, None
