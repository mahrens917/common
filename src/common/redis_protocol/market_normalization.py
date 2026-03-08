from __future__ import annotations

"""Normalization helpers for the Kalshi Redis protocol stores."""

import logging
import math
from datetime import datetime
from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Optional, Tuple

logger = logging.getLogger(__name__)

from common.exceptions import DataError, ValidationError

from ..market_filters.kalshi import extract_best_ask, extract_best_bid
from ..redis_schema import KalshiMarketDescriptor
from .kalshi_store.metadata_helpers.expiry_derivation import derive_expiry_iso_impl
from .kalshi_store.metadata_helpers.timestamp_normalization import select_timestamp_value
from .market_normalization_helpers import (
    compute_representative_strike,
    enrich_close_time,
    enrich_orderbook_defaults,
    enrich_status_field,
    enrich_strike_fields,
    extract_between_bounds,
    normalize_timestamp,
    parse_strike_segment,
    resolve_strike_type_from_prefix,
)
from .parsing import parse_expiry_token

NumericField = Optional[float]
StrikeFields = Optional[Tuple[str, Optional[float], Optional[float], float]]


class NumericFieldError(ValidationError, ValueError):
    """Raised when numeric field parsing fails."""


class ProbabilityValueError(ValueError):
    """Raised when probability value normalization fails."""


class ExpiryDerivationError(DataError, RuntimeError):
    """Raised when expiry cannot be derived from provided metadata."""


# Constants
_CONST_2 = 2
_CONST_4 = 4
_CONST_5 = 5


def convert_numeric_field(value: Any) -> NumericField:
    """
    Convert a value into a float, returning ``None`` when conversion fails or the
    original value is empty. Unsupported types raise ``ValueError``.
    """
    if value in (None, "", "None"):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return None
        try:
            return float(text)
        except ValueError as exc:
            raise NumericFieldError(f"Invalid numeric value: {value!r}") from exc
    if isinstance(value, Mapping):
        raise NumericFieldError(f"Unsupported numeric value type: {type(value).__name__}")
    raise TypeError(f"Unsupported numeric value type: {type(value).__name__}")


def normalise_hash(raw_hash: Mapping[Any, Any]) -> Dict[str, Any]:
    """Convert Redis hash responses to a ``str`` keyed dictionary."""

    normalised: Dict[str, Any] = {}
    for key, value in raw_hash.items():
        if isinstance(key, bytes):
            key = key.decode("utf-8", "ignore")
        if isinstance(value, bytes):
            value = value.decode("utf-8", "ignore")
        normalised[str(key)] = value
    return normalised


def sync_top_of_book_fields(snapshot: MutableMapping[str, Any]) -> None:
    """Align scalar YES-side fields with the JSON order book payload."""

    bid_price, bid_size = extract_best_bid(snapshot.get("yes_bids"))
    ask_price, ask_size = extract_best_ask(snapshot.get("yes_asks"))

    def _set_scalar(field: str, numeric: Optional[float | int]) -> None:
        if numeric is None:
            snapshot[field] = ""
        else:
            snapshot[field] = str(numeric)

    _set_scalar("yes_bid", bid_price)
    _set_scalar("yes_bid_size", bid_size)
    _set_scalar("yes_ask", ask_price)
    _set_scalar("yes_ask_size", ask_size)


def format_probability_value(value: Any) -> str:
    """Normalise probability payloads into compact decimal strings."""

    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ProbabilityValueError(f"Probability value must be numeric, got {value}") from exc

    if not math.isfinite(numeric):
        raise ProbabilityValueError(f"Probability value must be finite, got {numeric}")

    formatted = f"{numeric:.10f}"
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    if not formatted:
        return "0"
    return formatted


def derive_strike_fields(market_ticker: str) -> StrikeFields:
    """Extract strike information directly from the Kalshi ticker format."""
    tokens = _tokenize_ticker(market_ticker)
    if not tokens:
        return None
    strike_segment = tokens[-1]
    prefix, value_str = parse_strike_segment(strike_segment)
    strike_value = _coerce_strike_value(value_str)
    if strike_value is None:
        return None

    keyword_type = _resolve_keyword(tokens)
    strike_type, floor_strike, cap_strike = resolve_strike_type_from_prefix(prefix, keyword_type)
    floor_strike, cap_strike = _apply_prefix_bounds(prefix, strike_type, strike_value, floor_strike, cap_strike)

    if strike_type == "between":
        return _derive_between_fields(tokens, floor_strike, cap_strike, strike_value)
    return _finalize_non_between_fields(strike_type, floor_strike, cap_strike, strike_value)


def _tokenize_ticker(market_ticker: str) -> List[str]:
    return [segment for segment in market_ticker.upper().split("-") if segment]


def _coerce_strike_value(value_str: str) -> Optional[float]:
    try:
        return float(value_str)
    except ValueError as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Failed to coerce strike value to float: value_str=%r, error=%s", value_str, exc)
        return None


def _resolve_keyword(tokens: List[str]) -> Optional[str]:
    if "BETWEEN" in tokens:
        return "between"
    if any(token in {"LESS", "BELOW"} for token in tokens):
        return "less"
    if any(token in {"GREATER", "ABOVE"} for token in tokens):
        return "greater"
    return None


def _apply_prefix_bounds(
    prefix: str,
    strike_type: Optional[str],
    strike_value: float,
    floor_strike: Optional[float],
    cap_strike: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:
    upper_prefix = prefix.upper()
    if upper_prefix == "B":
        cap_strike = strike_value
    elif upper_prefix == "T":
        floor_strike = strike_value
    elif strike_type == "greater" and floor_strike is None:
        floor_strike = strike_value
    return floor_strike, cap_strike


def _derive_between_fields(
    tokens: List[str],
    floor_strike: Optional[float],
    cap_strike: Optional[float],
    strike_value: float,
) -> StrikeFields:
    between_floor, between_cap = extract_between_bounds(tokens)
    if between_floor is not None:
        floor_strike = between_floor
    if between_cap is not None:
        cap_strike = between_cap
    representative = compute_representative_strike(cap_strike, floor_strike, strike_value)
    return "between", floor_strike, cap_strike, representative


def _finalize_non_between_fields(
    strike_type: str,
    floor_strike: Optional[float],
    cap_strike: Optional[float],
    strike_value: float,
) -> StrikeFields:
    if strike_type == "less" and cap_strike is None:
        cap_strike = strike_value
    if strike_type == "greater" and floor_strike is None:
        floor_strike = strike_value
    return strike_type, floor_strike, cap_strike, strike_value


def derive_expiry_iso(
    market_ticker: str,
    metadata: Mapping[str, Any],
    *,
    descriptor: KalshiMarketDescriptor,
    token_parser: Optional[Callable[..., Optional[datetime]]] = None,
    now: Optional[datetime] = None,
) -> str:
    """Ensure we have an ISO formatted expiry/close time for downstream consumers."""
    try:
        return derive_expiry_iso_impl(
            market_ticker,
            dict(metadata),
            descriptor.expiry_token,
            now_dt=now,
            token_parser=token_parser,
        )
    except (
        DataError,
        RuntimeError,
    ) as exc:
        raise ExpiryDerivationError(str(exc)) from exc


def ensure_market_metadata_fields(
    market_ticker: str,
    metadata: Mapping[str, Any],
    *,
    descriptor: KalshiMarketDescriptor,
    token_parser: Optional[Callable[[str], Optional[datetime]]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Populate essential metadata fields when REST ingestion is missing."""
    enriched = dict(metadata)
    enriched.setdefault("ticker", market_ticker)

    # Enrich strike fields from ticker
    strike_details = derive_strike_fields(market_ticker)
    if strike_details is not None:
        strike_type, floor_strike, cap_strike, strike_value = strike_details
        enrich_strike_fields(enriched, strike_type, floor_strike, cap_strike, strike_value)

    # Enrich close time
    enrich_close_time(enriched, metadata)

    # Add default orderbook fields
    enrich_orderbook_defaults(enriched)

    # Add status field
    enrich_status_field(enriched, metadata)

    return enriched


__all__ = [
    "convert_numeric_field",
    "normalise_hash",
    "sync_top_of_book_fields",
    "format_probability_value",
    "parse_expiry_token",
    "derive_strike_fields",
    "normalize_timestamp",
    "derive_expiry_iso",
    "ensure_market_metadata_fields",
    "select_timestamp_value",
]
