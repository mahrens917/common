from __future__ import annotations

"""Shared Deribit instrument validators."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

MAX_RELATIVE_SPREAD = 0.35
MAX_QUOTE_AGE = timedelta(minutes=3)
MIN_LIQUIDITY = 1e-6


# --- Expiry checking ---


def normalize_expiry(value: Any) -> Optional[datetime]:
    """Normalize expiry to UTC timezone."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def is_expired(expiry: Optional[datetime], current_time: datetime) -> bool:
    """Check if instrument is expired."""
    return expiry is not None and expiry <= current_time


# --- Price validation ---


def validate_quotes(best_bid: Any, best_ask: Any, max_relative_spread: float) -> Optional[str]:
    """Validate bid/ask quotes. Returns failure reason or None if valid."""
    if best_bid is None or best_ask is None:
        return "missing_quotes"
    if best_bid <= 0 or best_ask <= 0:
        return "invalid_price"
    if best_ask <= best_bid:
        return "invalid_spread"
    mid_price = 0.5 * (best_bid + best_ask)
    spread = best_ask - best_bid
    if mid_price <= 0:
        return "invalid_price"
    relative_spread = spread / mid_price
    if relative_spread > max_relative_spread:
        return "wide_spread"
    return None


# --- Liquidity validation ---


def validate_sizes(bid_size: Any, ask_size: Any, min_liquidity: float) -> Optional[str]:
    """Validate bid/ask sizes. Returns failure reason or None if valid."""
    if bid_size is None or bid_size <= min_liquidity:
        return "missing_liquidity"
    if ask_size is None or ask_size <= min_liquidity:
        return "missing_liquidity"
    return None


# --- Quote timestamp validation ---


def extract_timestamp(instrument: Any) -> Optional[datetime]:
    """Extract quote timestamp from instrument."""
    quote_timestamp = getattr(instrument, "quote_timestamp", None) or getattr(instrument, "mark_price_timestamp", None)
    if quote_timestamp is None:
        quote_timestamp = getattr(instrument, "timestamp", None)
    return quote_timestamp


def validate_timestamp(quote_timestamp: Any, current_time: datetime, max_quote_age: timedelta) -> Optional[str]:
    """Validate quote timestamp. Returns failure reason or None if valid."""
    if not isinstance(quote_timestamp, datetime):
        return None
    normalized_ts = quote_timestamp
    if normalized_ts.tzinfo is None:
        normalized_ts = normalized_ts.replace(tzinfo=timezone.utc)
    if normalized_ts > current_time + timedelta(seconds=5):
        return "future_quote"
    if current_time - normalized_ts > max_quote_age:
        return "stale_quote"
    return None


# --- Composite validators ---


@dataclass
class DeribitOptionValidation:
    is_valid: bool
    reason: Optional[str] = None


@dataclass
class DeribitFutureValidation:
    is_valid: bool
    reason: Optional[str] = None


def validate_deribit_option(
    instrument: Any,
    *,
    now: Optional[datetime] = None,
) -> DeribitOptionValidation:
    current_time = now or datetime.now(timezone.utc)

    expiry = normalize_expiry(getattr(instrument, "expiry", None))
    if is_expired(expiry, current_time):
        return DeribitOptionValidation(False, reason="expired")

    best_bid = getattr(instrument, "best_bid", None)
    best_ask = getattr(instrument, "best_ask", None)
    price_error = validate_quotes(best_bid, best_ask, MAX_RELATIVE_SPREAD)
    if price_error:
        return DeribitOptionValidation(False, reason=price_error)

    bid_size = getattr(instrument, "best_bid_size", None)
    ask_size = getattr(instrument, "best_ask_size", None)
    liquidity_error = validate_sizes(bid_size, ask_size, MIN_LIQUIDITY)
    if liquidity_error:
        return DeribitOptionValidation(False, reason=liquidity_error)

    quote_timestamp = extract_timestamp(instrument)
    timestamp_error = validate_timestamp(quote_timestamp, current_time, MAX_QUOTE_AGE)
    if timestamp_error:
        return DeribitOptionValidation(False, reason=timestamp_error)

    return DeribitOptionValidation(True)


def validate_deribit_future(
    instrument: Any,
    *,
    now: Optional[datetime] = None,
) -> DeribitFutureValidation:
    current_time = now or datetime.now(timezone.utc)

    expiry = normalize_expiry(getattr(instrument, "expiry", None))
    if is_expired(expiry, current_time):
        return DeribitFutureValidation(False, reason="expired")

    best_bid = getattr(instrument, "best_bid", None)
    best_ask = getattr(instrument, "best_ask", None)

    if best_bid is None:
        return DeribitFutureValidation(False, reason="missing_bid")
    if best_ask is None:
        return DeribitFutureValidation(False, reason="missing_ask")
    if best_bid <= 0 or best_ask <= 0:
        return DeribitFutureValidation(False, reason="invalid_price")
    if best_ask <= best_bid:
        return DeribitFutureValidation(False, reason="invalid_spread")

    return DeribitFutureValidation(True)


__all__ = [
    "DeribitOptionValidation",
    "DeribitFutureValidation",
    "validate_deribit_option",
    "validate_deribit_future",
    "normalize_expiry",
    "is_expired",
    "validate_quotes",
    "validate_sizes",
    "extract_timestamp",
    "validate_timestamp",
]
