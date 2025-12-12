"""
Shared utility functions for KalshiStore

This module contains static helper methods and utility functions that are shared
across multiple KalshiStore components. All functions are stateless and can be
used independently.
"""

import logging
import math
from collections import Counter
from typing import Any, Dict, List, Optional

from common.exceptions import ValidationError

from ...config.weather import WeatherConfigError, load_weather_station_mapping
from ...market_filters.kalshi import extract_best_ask, extract_best_bid
from .utils_coercion_helpers.type_coercion import bool_or_default as _bool_or_default_impl
from .utils_coercion_helpers.type_coercion import coerce_mapping as _coerce_mapping_impl
from .utils_coercion_helpers.type_coercion import coerce_sequence as _coerce_sequence_impl
from .utils_coercion_helpers.type_coercion import float_or_default as _float_or_default_impl
from .utils_coercion_helpers.type_coercion import int_or_default as _int_or_default_impl
from .utils_coercion_helpers.type_coercion import string_or_default as _string_or_default_impl

logger = logging.getLogger(__name__)

__all__ = [
    "default_weather_station_loader",
    "bool_or_default",
    "coerce_mapping",
    "coerce_sequence",
    "convert_numeric_field",
    "_convert_numeric_field",
    "_coerce_mapping",
    "_string_or_default",
    "_int_or_default",
    "_float_or_default",
    "int_or_default",
    "string_or_default",
    "float_or_default",
    "_counter_value",
    "_to_optional_float",
    "to_optional_float",
    "_normalise_hash",
    "_sync_top_of_book_fields",
    "_format_probability_value",
    "_normalize_timestamp",
    "normalise_hash",
    "sync_top_of_book_fields",
    "format_probability_value",
    "normalize_timestamp",
    "_select_timestamp_value",
]


# ============================================================================
# Module-level Configuration Loaders
# ============================================================================
def default_weather_station_loader() -> Dict[str, Dict[str, Any]]:  # pragma: no cover - config I/O
    """
    Load the weather station mapping from configuration.

    The loader fails fast—any configuration error stops KalshiStore initialisation.
    """
    try:
        return load_weather_station_mapping()
    except WeatherConfigError:  # policy_guard: allow-silent-handler
        logger.exception("Weather station mapping unavailable; aborting KalshiStore initialisation")
        raise
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
    ) as exc:  # pragma: no cover - configuration guardrail
        logger.exception("Unexpected error loading weather station mapping; aborting KalshiStore initialisation")
        raise WeatherConfigError("Weather station mapping loading failed unexpectedly") from exc


_default_weather_station_loader = default_weather_station_loader


def _default_weather_station_loader() -> Dict[str, Dict[str, Any]]:
    """Alias used by internal KalshiStore initializers."""
    return default_weather_station_loader()


def _convert_numeric_field(value: Any) -> Optional[float]:  # pragma: no cover - numeric helper
    """
    Convert a field value to numeric format for proper data storage.

    Delegates to canonical implementation in common.utils.numeric.

    Args:
        value: The value to convert (can be string, number, or None)

    Returns:
        Numeric value or None if empty/invalid
    """
    from common.utils.numeric import coerce_float_optional

    if value is None or value in ("", "None"):
        return None

    try:
        return coerce_float_optional(value)
    except (ValueError, TypeError) as exc:  # policy_guard: allow-silent-handler
        raise ValidationError(f"Invalid numeric value: {value!r}") from exc


def convert_numeric_field(value: Any) -> Optional[float]:
    """Public wrapper for numeric conversion helper."""
    return _convert_numeric_field(value)


# ============================================================================
# Type Coercion Utilities
# ============================================================================


def _coerce_mapping(candidate: Any) -> Dict[str, Any]:
    """Convert candidate to dict, returning empty dict if not a dict."""
    if isinstance(candidate, dict):
        return candidate
    return {}


def coerce_mapping(candidate: Any) -> Dict[str, Any]:
    """
    Convert candidate to dict, returning empty dict if conversion fails.

    Accepts mapping-like objects that expose ``items``.
    """
    return _coerce_mapping_impl(candidate)


def coerce_sequence(candidate: Any) -> List[Any]:
    """Convert candidate to a list, falling back to empty list on failure."""
    return _coerce_sequence_impl(candidate)


def _string_or_default(value: Any, fallback_value: str = "") -> str:
    """
    Coerce value to string with fallback value.

    Args:
        value: Value to coerce
        fallback_value: Fallback value if value is None

    Returns:
        String representation or fallback value
    """
    return str(value) if value is not None else fallback_value


def string_or_default(value: Any, fallback_value: str = "", *, trim: bool = False) -> str:
    """Coerce value to string with optional whitespace trimming and byte decoding."""
    return _string_or_default_impl(value, fallback_value, trim=trim)


def _int_or_default(value: Any, fallback_value: int = 0) -> int:
    """
    Coerce value to int with fallback value.

    Args:
        value: Value to coerce
        fallback_value: Fallback value if coercion fails

    Returns:
        Integer representation or fallback value
    """
    return _int_or_default_impl(value, fallback_value)


def int_or_default(value: Any, fallback_value: int = 0) -> int:
    """Public wrapper for int coercion helper."""
    return _int_or_default_impl(value, fallback_value)


def _float_or_default(value: Any, fallback_value: float = 0.0) -> float:
    """
    Coerce value to float with optional fallback value.

    Delegates to canonical implementation in common.utils.numeric.

    Args:
        value: Value to coerce
        fallback_value: Fallback value if coercion fails

    Returns:
        Float representation or fallback value
    """
    from common.utils.numeric import coerce_float_default

    return coerce_float_default(value, fallback_value)


def float_or_default(
    value: Any,
    fallback_value: float = 0.0,
    *,
    raise_on_error: bool = False,
    error_message: str | None = None,
) -> float:
    """
    Coerce value to float with optional error raising.

    Delegates to canonical implementation in common.utils.numeric.

    When ``raise_on_error`` is False (default), this mirrors ``_float_or_default`` and
    returns the provided ``fallback_value`` for invalid inputs. When True, a ``ValueError`` is
    raised using ``error_message`` if provided.
    """
    return _float_or_default_impl(value, fallback_value, raise_on_error=raise_on_error, error_message=error_message)


def bool_or_default(
    value: Any,
    fallback_value: bool,
    *,
    parse_strings: bool = False,
) -> bool:
    """
    Coerce common boolean representations or return fallback value.

    When ``parse_strings`` is True, accepts typical truthy/falsey strings.
    """
    return _bool_or_default_impl(value, fallback_value, parse_strings=parse_strings)


def _counter_value(counter: Counter[str], key: str) -> int:
    """
    Get counter value with default of 0.

    Args:
        counter: Counter object
        key: Key to lookup

    Returns:
        Counter value or 0 if key not found
    """
    if key in counter:
        return counter[key]
    return 0


def _to_optional_float(value: Any, *, context: str) -> Optional[float]:
    """
    Convert value to optional float with context for error messages.

    Args:
        value: Value to convert
        context: Context string for error messages

    Returns:
        Float value or None if empty

    Raises:
        RuntimeError: If value is invalid
    """
    if value in (None, "", b""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
        raise RuntimeError(f"Invalid {context} value: {value}") from exc


def to_optional_float(value: Any, *, context: str) -> Optional[float]:
    """
    Convert value to optional float with context for error messages.

    Args:
        value: Value to convert
        context: Context string for error messages

    Returns:
        Float value or None if empty

    Raises:
        RuntimeError: If value is invalid
    """
    return _to_optional_float(value, context=context)


# ============================================================================
# Redis Hash Utilities
# ============================================================================


def _normalise_hash(raw_hash: Dict[Any, Any]) -> Dict[str, Any]:
    """
    Convert Redis hash responses to a str-keyed dictionary.

    Delegates to canonical implementation in market_normalization_core.

    Args:
        raw_hash: Raw hash from Redis (may have bytes keys/values)

    Returns:
        Normalized dictionary with string keys and decoded values
    """
    from ..market_normalization_core import normalise_hash

    return normalise_hash(raw_hash)


def normalise_hash(raw_hash: Dict[Any, Any]) -> Dict[str, Any]:
    """
    Public wrapper for Redis hash normalization.
    """
    return _normalise_hash(raw_hash)


# ============================================================================
# Orderbook Utilities
# ============================================================================


def _sync_top_of_book_fields(snapshot: Dict[str, Any]) -> None:
    """
    Align scalar YES side fields with the JSON orderbook payload.

    Modifies snapshot in-place to ensure scalar fields match orderbook data.

    Args:
        snapshot: Market snapshot dictionary to update
    """
    bid_price, bid_size = extract_best_bid(snapshot.get("yes_bids"))
    ask_price, ask_size = extract_best_ask(snapshot.get("yes_asks"))

    def _set_scalar(field: str, value: Optional[float | int]) -> None:
        if value is None:
            snapshot[field] = ""
        else:
            snapshot[field] = str(value)

    _set_scalar("yes_bid", bid_price)
    _set_scalar("yes_bid_size", bid_size)
    _set_scalar("yes_ask", ask_price)
    _set_scalar("yes_ask_size", ask_size)


def sync_top_of_book_fields(snapshot: Dict[str, Any]) -> None:
    """
    Public wrapper for top-of-book field synchronization.
    """
    _sync_top_of_book_fields(snapshot)


# ============================================================================
# Formatting Utilities
# ============================================================================


def _format_probability_value(value: Any) -> str:
    """
    Format probability value for storage.

    Args:
        value: Probability value to format

    Returns:
        Formatted probability string

    Raises:
        ValueError: If value is not float-compatible or not finite
    """
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
        raise TypeError(f"Probability value must be float-compatible, got {value}") from exc

    if not math.isfinite(numeric):
        raise TypeError(f"Probability value must be finite, got {numeric}")

    formatted = f"{numeric:.10f}"
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    if not formatted:
        return "0"
    return formatted


def format_probability_value(value: Any) -> str:
    """
    Public wrapper for probability value formatting.
    """
    return _format_probability_value(value)


# ============================================================================
# Timestamp Utilities
# ============================================================================


def _normalize_timestamp(value: Any) -> Optional[str]:
    """
    Normalize timestamp format to ISO8601.

    Delegates to canonical implementation in metadata_helpers.timestamp_normalization.

    Args:
        value: Timestamp value (string, int, float, or datetime)

    Returns:
        ISO8601 formatted timestamp or None if invalid
    """
    from .metadata_helpers.timestamp_normalization import normalize_timestamp

    return normalize_timestamp(value)


def normalize_timestamp(value: Any) -> Optional[str]:
    """
    Public wrapper for timestamp normalization.
    """
    return _normalize_timestamp(value)


def _select_timestamp_value(market_data: Dict, fields: List[str]) -> Optional[object]:
    """
    Select timestamp from market data by trying multiple field names.

    Args:
        market_data: Market data dictionary
        fields: List of field names to try in order

    Returns:
        First non-None timestamp value found or None
    """
    from .metadata import KalshiMetadataAdapter

    return KalshiMetadataAdapter.select_timestamp_value(market_data, fields)


# ============================================================================
# Market Metadata Parsing
# ============================================================================
