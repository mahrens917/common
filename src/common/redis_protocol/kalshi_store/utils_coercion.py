"""
Shared utility functions for KalshiStore

This module contains static helper methods and utility functions that are shared
across multiple KalshiStore components. All functions are stateless and can be
used independently.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List, Optional

from common.exceptions import ValidationError

from ...config.weather import WeatherConfigError, load_weather_station_mapping
from ...market_filters.kalshi import extract_best_ask, extract_best_bid
from .utils_coercion_helpers import (
    bool_or_default,
    coerce_mapping,
    coerce_sequence,
    float_or_default,
    int_or_default,
    string_or_default,
)

logger = logging.getLogger(__name__)

__all__ = [
    "default_weather_station_loader",
    "bool_or_default",
    "coerce_mapping",
    "coerce_sequence",
    "convert_numeric_field",
    "int_or_default",
    "string_or_default",
    "float_or_default",
    "to_optional_float",
    "normalise_hash",
    "sync_top_of_book_fields",
    "format_probability_value",
    "normalize_timestamp",
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
    except WeatherConfigError:
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


def convert_numeric_field(value: Any) -> Optional[float]:  # pragma: no cover - numeric helper
    """Convert a field value to numeric format for proper data storage."""
    from common.utils.numeric import coerce_float_optional

    if value is None or value in ("", "None"):
        return None

    try:
        return coerce_float_optional(value)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Invalid numeric value: {value!r}") from exc


# ============================================================================
# Type Coercion Utilities
# ============================================================================


def _counter_value(counter: Counter[str], key: str) -> int:
    """Get counter value with a default of 0."""
    if key in counter:
        return counter[key]
    return 0


def to_optional_float(value: Any, *, context: str) -> Optional[float]:
    """Convert value to optional float with context for error messages."""
    if value in (None, "", b""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid {context} value: {value}") from exc


# ============================================================================
# Redis Hash Utilities
# ============================================================================


def normalise_hash(raw_hash: Dict[Any, Any]) -> Dict[str, Any]:
    """Convert Redis hash responses to a str-keyed dictionary."""
    from ..market_normalization_core import normalise_hash as _canonical

    return _canonical(raw_hash)


# ============================================================================
# Orderbook Utilities
# ============================================================================


def _sync_top_of_book_fields(snapshot: Dict[str, Any]) -> None:
    """Align scalar YES side fields with the JSON orderbook payload."""
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


def format_probability_value(value: Any) -> str:
    """Format probability value for storage. Delegates to canonical implementation."""
    from ..market_normalization_core import format_probability_value as _canonical

    return _canonical(value)


# ============================================================================
# Timestamp Utilities
# ============================================================================


def normalize_timestamp(value: Any) -> Optional[str]:
    """Re-export of canonical normalize_timestamp for public API compatibility."""
    from .metadata_helpers.timestamp_normalization import normalize_timestamp as _canonical

    return _canonical(value)


_normalize_timestamp = normalize_timestamp


def _select_timestamp_value(market_data: Dict, fields: List[str]) -> Optional[object]:
    """Select timestamp from market data by trying multiple field names."""
    from .metadata_helpers.timestamp_normalization import select_timestamp_value

    return select_timestamp_value(market_data, fields)


# ============================================================================
# Market Metadata Parsing
# ============================================================================
