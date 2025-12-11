from __future__ import annotations

"""Shared Deribit instrument validators."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


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
    from .deribit_helpers import (
        ExpiryChecker,
        LiquidityValidator,
        PriceValidator,
        QuoteTimestampValidator,
    )

    current_time = now or datetime.now(timezone.utc)

    # Check expiry
    expiry = ExpiryChecker.normalize_expiry(getattr(instrument, "expiry", None))
    if ExpiryChecker.is_expired(expiry, current_time):
        return DeribitOptionValidation(False, reason="expired")

    # Validate prices
    best_bid = getattr(instrument, "best_bid", None)
    best_ask = getattr(instrument, "best_ask", None)
    price_error = PriceValidator.validate_quotes(best_bid, best_ask, MAX_RELATIVE_SPREAD)
    if price_error:
        return DeribitOptionValidation(False, reason=price_error)

    # Validate liquidity
    bid_size = getattr(instrument, "best_bid_size", None)
    ask_size = getattr(instrument, "best_ask_size", None)
    liquidity_error = LiquidityValidator.validate_sizes(bid_size, ask_size, MIN_LIQUIDITY)
    if liquidity_error:
        return DeribitOptionValidation(False, reason=liquidity_error)

    # Validate quote timestamp
    quote_timestamp = QuoteTimestampValidator.extract_timestamp(instrument)
    timestamp_error = QuoteTimestampValidator.validate_timestamp(quote_timestamp, current_time, MAX_QUOTE_AGE)
    if timestamp_error:
        return DeribitOptionValidation(False, reason=timestamp_error)

    return DeribitOptionValidation(True)


def validate_deribit_future(
    instrument: Any,
    *,
    now: Optional[datetime] = None,
) -> DeribitFutureValidation:
    from .deribit_helpers import ExpiryChecker

    current_time = now or datetime.now(timezone.utc)

    # Check expiry
    expiry = ExpiryChecker.normalize_expiry(getattr(instrument, "expiry", None))
    if ExpiryChecker.is_expired(expiry, current_time):
        return DeribitFutureValidation(False, reason="expired")

    # Validate bid/ask presence and values
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
]
MAX_RELATIVE_SPREAD = 0.35
MAX_QUOTE_AGE = timedelta(minutes=3)
MIN_LIQUIDITY = 1e-6
