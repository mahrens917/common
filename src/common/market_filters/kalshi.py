from __future__ import annotations

from common.truthy import pick_if

"""Centralised validators for Kalshi market metadata."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

from common.redis_schema import is_supported_kalshi_ticker

from .kalshi_helpers import (
    compute_strike_value,
    parse_expiry,
    validate_expiry,
    validate_pricing_data,
    validate_strike_type,
    validate_ticker_support,
)
from .kalshi_helpers.data_converters import (
    decode_payload,
    parse_expiry_datetime,
    to_float_value,
    to_int_value,
)

_DEFAULT_INVALID_EXPIRY_REASON = "invalid_expiry"
_DEFAULT_UNSUPPORTED_TICKER_REASON = "unsupported_ticker"
_DEFAULT_UNKNOWN_STRIKE_TYPE_REASON = "unknown_strike_type"
_DEFAULT_STRIKE_VALIDATION_FAILED_REASON = "strike_validation_failed"
_DEFAULT_PRICING_VALIDATION_FAILED_REASON = "pricing_validation_failed"


@dataclass(frozen=True)
class _StrikeInfo:
    """Strike and expiry information for market validation."""

    expiry_dt: datetime
    expiry_raw: str
    strike: float
    strike_type_lower: str
    floor_strike: Optional[float]
    cap_strike: Optional[float]


def _normalise_orderbook(payload: Any) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return payload
    if isinstance(payload, (str, bytes)):
        text = decode_payload(payload)
        if not text:
            return {}
        try:
            deserialised = json.loads(text)
            if isinstance(deserialised, Mapping):
                return deserialised
        except json.JSONDecodeError:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.debug("Expected exception in operation")
            return {}
    return {}


def extract_best_bid(payload: Any) -> Tuple[Optional[float], Optional[int]]:
    book = _normalise_orderbook(payload)
    best_price: Optional[float] = None
    best_size: Optional[int] = None
    for price_str, size in book.items():
        price = to_float_value(price_str)
        size_int = to_int_value(size)
        if price is None or size_int is None or size_int <= 0:
            continue
        if best_price is None or price > best_price:
            best_price = price
            best_size = size_int
    return best_price, best_size


def extract_best_ask(payload: Any) -> Tuple[Optional[float], Optional[int]]:
    book = _normalise_orderbook(payload)
    best_price: Optional[float] = None
    best_size: Optional[int] = None
    for price_str, size in book.items():
        price = to_float_value(price_str)
        size_int = to_int_value(size)
        if price is None or size_int is None or size_int <= 0:
            continue
        if best_price is None or price < best_price:
            best_price = price
            best_size = size_int
    return best_price, best_size


# parse_expiry_datetime is imported from kalshi_helpers.data_converters


@dataclass
class KalshiMarketValidation:
    is_valid: bool
    reason: Optional[str] = None
    expiry: Optional[datetime] = None
    expiry_raw: Optional[str] = None
    strike: Optional[float] = None
    strike_type: Optional[str] = None
    floor_strike: Optional[float] = None
    cap_strike: Optional[float] = None
    yes_bid_price: Optional[float] = None
    yes_bid_size: Optional[int] = None
    yes_ask_price: Optional[float] = None
    yes_ask_size: Optional[int] = None
    last_price: Optional[float] = None
    has_orderbook: bool = False


def _resolve_top_of_book(
    metadata: Mapping[str, Any],
    orderbook: Optional[Mapping[str, Any]],
) -> Tuple[Tuple[Optional[float], Optional[int]], Tuple[Optional[float], Optional[int]], bool]:
    bids_payload: Any = None
    asks_payload: Any = None
    if orderbook:
        bids_payload = orderbook.get("yes_bids")
        asks_payload = orderbook.get("yes_asks")

    bid_from_book = pick_if(bids_payload is not None, lambda: extract_best_bid(bids_payload), lambda: (None, None))
    ask_from_book = pick_if(asks_payload is not None, lambda: extract_best_ask(asks_payload), lambda: (None, None))

    has_orderbook = any(value is not None for value in bid_from_book + ask_from_book)

    bid_price, bid_size = bid_from_book
    ask_price, ask_size = ask_from_book

    if bid_price is None:
        bid_price = to_float_value(metadata.get("yes_bid"))
        bid_size = to_int_value(metadata.get("yes_bid_size")) if bid_size is None else bid_size
    if ask_price is None:
        ask_price = to_float_value(metadata.get("yes_ask"))
        ask_size = to_int_value(metadata.get("yes_ask_size")) if ask_size is None else ask_size

    return (bid_price, bid_size), (ask_price, ask_size), has_orderbook


def _invalid_market(
    *,
    reason: str,
    expiry: Optional[datetime] = None,
    expiry_raw: Optional[str] = None,
    strike: Optional[float] = None,
    strike_type: Optional[str] = None,
    floor_strike: Optional[float] = None,
    cap_strike: Optional[float] = None,
) -> KalshiMarketValidation:
    """Return a standardized invalid market result."""
    return KalshiMarketValidation(
        False,
        reason=reason,
        expiry=expiry,
        expiry_raw=expiry_raw,
        strike=strike,
        strike_type=strike_type,
        floor_strike=floor_strike,
        cap_strike=cap_strike,
    )


def _validate_and_parse_expiry(metadata: Mapping[str, Any], current_time: datetime) -> KalshiMarketValidation | tuple[str, datetime]:
    """Parse expiry fields and ensure they are valid."""
    expiry_raw, expiry_dt = parse_expiry(metadata)
    if not expiry_raw:
        return _invalid_market(reason="missing_close_time")

    if expiry_dt is None:
        return _invalid_market(reason="unparseable_expiry", expiry_raw=expiry_raw)

    is_valid_expiry, expiry_reason = validate_expiry(expiry_dt, current_time)
    if not is_valid_expiry:
        return _invalid_market(
            reason=expiry_reason if expiry_reason is not None else _DEFAULT_INVALID_EXPIRY_REASON,
            expiry=expiry_dt,
            expiry_raw=expiry_raw,
        )

    return expiry_raw, expiry_dt


def _validate_ticker(
    metadata: Mapping[str, Any],
    expiry_dt: datetime,
    expiry_raw: str,
) -> Optional[KalshiMarketValidation]:
    """Ensure ticker is supported for downstream systems."""
    is_valid_ticker, ticker_reason = validate_ticker_support(metadata, is_supported_kalshi_ticker)
    if not is_valid_ticker:
        return _invalid_market(
            reason=ticker_reason if ticker_reason is not None else _DEFAULT_UNSUPPORTED_TICKER_REASON,
            expiry=expiry_dt,
            expiry_raw=expiry_raw,
        )
    return None


def _validate_strike_type(
    metadata: Mapping[str, Any],
    expiry_dt: datetime,
    expiry_raw: str,
) -> KalshiMarketValidation | str:
    """Ensure strike type field exists and is supported."""
    has_strike_type, strike_reason, strike_type_lower = validate_strike_type(metadata)
    if not has_strike_type:
        return _invalid_market(
            reason=strike_reason if strike_reason is not None else _DEFAULT_UNKNOWN_STRIKE_TYPE_REASON,
            expiry=expiry_dt,
            expiry_raw=expiry_raw,
        )
    if strike_type_lower is None:
        return _invalid_market(
            reason="unknown_strike_type",
            expiry=expiry_dt,
            expiry_raw=expiry_raw,
        )
    return strike_type_lower


def _compute_and_validate_strike(
    strike_type_lower: str,
    metadata: Mapping[str, Any],
    expiry_dt: datetime,
    expiry_raw: str,
) -> KalshiMarketValidation | tuple[float, Optional[float], Optional[float]]:
    """Compute strike/floor/cap values."""
    is_valid_strike, strike_error, strike, floor_strike, cap_strike = compute_strike_value(strike_type_lower, metadata)
    if not is_valid_strike:
        return _invalid_market(
            reason=strike_error if strike_error is not None else _DEFAULT_STRIKE_VALIDATION_FAILED_REASON,
            expiry=expiry_dt,
            expiry_raw=expiry_raw,
            strike_type=strike_type_lower,
        )
    if strike is None:
        return _invalid_market(
            reason="strike_validation_failed",
            expiry=expiry_dt,
            expiry_raw=expiry_raw,
            strike_type=strike_type_lower,
        )
    return strike, floor_strike, cap_strike


def _resolve_and_validate_pricing(
    metadata: Mapping[str, Any],
    orderbook: Optional[Mapping[str, Any]],
    require_pricing: bool,
    strike_info: "_StrikeInfo",
) -> KalshiMarketValidation | tuple[Optional[float], Optional[int], Optional[float], Optional[int], bool]:
    """Resolve best bid/ask and ensure pricing meets requirements."""
    (bid_price, bid_size), (ask_price, ask_size), has_orderbook = _resolve_top_of_book(metadata, orderbook)

    is_valid_pricing, pricing_reason = validate_pricing_data(bid_price, bid_size, ask_price, ask_size, require_pricing)
    if not is_valid_pricing:
        return _invalid_market(
            reason=pricing_reason if pricing_reason is not None else _DEFAULT_PRICING_VALIDATION_FAILED_REASON,
            expiry=strike_info.expiry_dt,
            expiry_raw=strike_info.expiry_raw,
            strike=strike_info.strike,
            strike_type=strike_info.strike_type_lower,
            floor_strike=strike_info.floor_strike,
            cap_strike=strike_info.cap_strike,
        )

    return bid_price, bid_size, ask_price, ask_size, has_orderbook


@dataclass(frozen=True)
class _PricingData:
    """Pricing data for market validation."""

    bid_price: Optional[float]
    bid_size: Optional[int]
    ask_price: Optional[float]
    ask_size: Optional[int]
    has_orderbook: bool


def _build_successful_validation(
    strike_info: _StrikeInfo,
    pricing: _PricingData,
) -> KalshiMarketValidation:
    """Assemble the final successful validation response."""
    from .kalshi_helpers.pricing_validator import check_side_validity

    has_bid = check_side_validity(pricing.bid_price, pricing.bid_size)
    has_ask = check_side_validity(pricing.ask_price, pricing.ask_size)

    return KalshiMarketValidation(
        True,
        expiry=strike_info.expiry_dt,
        expiry_raw=strike_info.expiry_raw,
        strike=strike_info.strike,
        strike_type=strike_info.strike_type_lower,
        floor_strike=strike_info.floor_strike,
        cap_strike=strike_info.cap_strike,
        yes_bid_price=pricing.bid_price if has_bid else None,
        yes_bid_size=pricing.bid_size if has_bid else None,
        yes_ask_price=pricing.ask_price if has_ask else None,
        yes_ask_size=pricing.ask_size if has_ask else None,
        last_price=None,
        has_orderbook=pricing.has_orderbook,
    )


def _run_validation_chain(
    metadata: Mapping[str, Any],
    current_time: datetime,
    orderbook: Optional[Mapping[str, Any]],
    require_pricing: bool,
) -> KalshiMarketValidation:
    """Run the full validation chain and return the final result."""
    expiry_result = _validate_and_parse_expiry(metadata, current_time)
    if isinstance(expiry_result, KalshiMarketValidation):
        return expiry_result
    expiry_raw, expiry_dt = expiry_result

    ticker_failure = _validate_ticker(metadata, expiry_dt, expiry_raw)
    if ticker_failure:
        return ticker_failure

    strike_type_result = _validate_strike_type(metadata, expiry_dt, expiry_raw)
    if isinstance(strike_type_result, KalshiMarketValidation):
        return strike_type_result
    strike_type_lower = strike_type_result

    strike_result = _compute_and_validate_strike(strike_type_lower, metadata, expiry_dt, expiry_raw)
    if isinstance(strike_result, KalshiMarketValidation):
        return strike_result
    strike, floor_strike, cap_strike = strike_result

    strike_info = _StrikeInfo(
        expiry_dt=expiry_dt,
        expiry_raw=expiry_raw,
        strike=strike,
        strike_type_lower=strike_type_lower,
        floor_strike=floor_strike,
        cap_strike=cap_strike,
    )

    pricing_result = _resolve_and_validate_pricing(
        metadata,
        orderbook,
        require_pricing,
        strike_info,
    )
    if isinstance(pricing_result, KalshiMarketValidation):
        return pricing_result
    bid_price, bid_size, ask_price, ask_size, has_orderbook = pricing_result

    pricing = _PricingData(
        bid_price=bid_price,
        bid_size=bid_size,
        ask_price=ask_price,
        ask_size=ask_size,
        has_orderbook=has_orderbook,
    )

    return _build_successful_validation(strike_info, pricing)


def validate_kalshi_market(
    metadata: Mapping[str, Any],
    *,
    now: Optional[datetime] = None,
    orderbook: Optional[Mapping[str, Any]] = None,
    require_pricing: bool = True,
) -> KalshiMarketValidation:
    if not metadata:
        return _invalid_market(reason="empty_data")

    current_time = now or datetime.now(timezone.utc)
    return _run_validation_chain(metadata, current_time, orderbook, require_pricing)


__all__ = [
    "KalshiMarketValidation",
    "validate_kalshi_market",
    "extract_best_bid",
    "extract_best_ask",
    "parse_expiry_datetime",
    "decode_payload",
    "to_float_value",
    "to_int_value",
]
