"""Conversion helpers for creating MicroPriceOptionData from enhanced option data."""

from datetime import datetime, timezone
from typing import Any, Tuple

from .errors import OptionDataConversionError


def resolve_instrument_name(enhanced_option: Any) -> str:
    """Extract instrument name from enhanced option data."""
    if hasattr(enhanced_option, "instrument_name"):
        instrument_name = enhanced_option.instrument_name
        if instrument_name:
            return str(instrument_name)
    return "unknown"


def determine_underlying(enhanced_option: Any, instrument_name: str) -> str:
    """Determine underlying asset from enhanced option data."""
    underlying = getattr(enhanced_option, "underlying", None)
    if underlying:
        return str(underlying)

    if instrument_name and instrument_name != "unknown":
        parts = instrument_name.split("-")
        if parts and parts[0] in {"BTC", "ETH"}:
            return parts[0]
    raise OptionDataConversionError("Enhanced option data must provide an 'underlying' field or a parseable instrument name")


def determine_expiry(enhanced_option: Any) -> datetime:
    """Extract and convert expiry datetime from enhanced option data."""
    expiry_candidate = None
    if hasattr(enhanced_option, "expiry_timestamp"):
        expiry_candidate = getattr(enhanced_option, "expiry_timestamp")
    elif hasattr(enhanced_option, "expiry"):
        expiry_candidate = getattr(enhanced_option, "expiry")
        if isinstance(expiry_candidate, datetime):
            return expiry_candidate.astimezone(timezone.utc)

    if expiry_candidate is None:
        raise OptionDataConversionError("Enhanced option data must include 'expiry' or 'expiry_timestamp'")

    try:
        timestamp = int(expiry_candidate)
    except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
        raise OptionDataConversionError("Expiry timestamp must be an integer") from exc
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def resolve_option_type(enhanced_option: Any) -> str:
    """Extract and normalize option type from enhanced option data."""
    if hasattr(enhanced_option, "option_type"):
        option_type = enhanced_option.option_type
    else:
        option_type = "call"
    normalized = str(option_type).lower()
    if normalized not in {"call", "put"}:
        raise OptionDataConversionError(f"Unsupported option type: {option_type}")
    return normalized


def extract_prices(enhanced_option: Any) -> Tuple[float, float]:
    """Extract bid and ask prices from enhanced option data."""
    if hasattr(enhanced_option, "best_bid") and hasattr(enhanced_option, "best_ask"):
        best_bid, best_ask = enhanced_option.best_bid, enhanced_option.best_ask
    elif hasattr(enhanced_option, "bid_price") and hasattr(enhanced_option, "ask_price"):
        best_bid, best_ask = enhanced_option.bid_price, enhanced_option.ask_price
    else:
        raise OptionDataConversionError("Enhanced option data must have bid/ask price fields")

    try:
        bid, ask = float(best_bid), float(best_ask)
    except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
        raise OptionDataConversionError("Bid/ask prices must be numeric") from exc

    if bid < 0 or ask < 0:
        raise OptionDataConversionError(f"Bid/ask must be non-negative: {bid}, {ask}")
    if ask < bid:
        raise OptionDataConversionError(f"Ask ({ask}) must be >= bid ({bid})")
    return bid, ask


def extract_sizes(enhanced_option: Any) -> Tuple[float, float]:
    """Extract bid and ask sizes from enhanced option data."""
    bid_size = getattr(enhanced_option, "best_bid_size", getattr(enhanced_option, "bid_size", None))
    ask_size = getattr(enhanced_option, "best_ask_size", getattr(enhanced_option, "ask_size", None))
    if bid_size is None or ask_size is None:
        raise OptionDataConversionError("Enhanced option data must include bid/ask sizes")

    try:
        bid, ask = float(bid_size), float(ask_size)
    except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
        raise OptionDataConversionError("Bid/ask sizes must be numeric") from exc
    if bid <= 0 or ask <= 0:
        raise OptionDataConversionError(f"Bid/ask sizes must be positive: {bid}, {ask}")
    return bid, ask


def resolve_timestamp(enhanced_option: Any) -> datetime:
    """Extract timestamp from enhanced option data or use current time."""
    from ...time_utils import get_current_utc

    timestamp = getattr(enhanced_option, "timestamp", get_current_utc())
    if isinstance(timestamp, datetime):
        return timestamp.astimezone(timezone.utc)
    try:
        return datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
        raise OptionDataConversionError("Timestamp must be datetime or epoch") from exc


class MicroPriceConversionHelpers:
    """Helper methods for converting enhanced option data to MicroPriceOptionData."""

    resolve_instrument_name = staticmethod(resolve_instrument_name)
    determine_underlying = staticmethod(determine_underlying)
    determine_expiry = staticmethod(determine_expiry)
    resolve_option_type = staticmethod(resolve_option_type)
    extract_prices = staticmethod(extract_prices)
    extract_sizes = staticmethod(extract_sizes)
    resolve_timestamp = staticmethod(resolve_timestamp)
