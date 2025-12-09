from __future__ import annotations

"""Timestamp normalization utilities.

Delegates to canonical implementation in kalshi_store.utils_market.
"""

from typing import Any, Dict, List, Optional

from ..utils_market import normalise_trade_timestamp


def normalize_timestamp(value: Any) -> Optional[str]:
    """
    Normalize a timestamp value to ISO8601 format.

    Delegates to canonical implementation in utils_market._normalise_trade_timestamp.

    Handles:
    - Unix timestamps (seconds or milliseconds)
    - ISO8601 strings
    - Empty/None values
    - Invalid strings are passed through unchanged

    Returns None for empty/None values, original string for invalid formats.
    """
    if value in (None, ""):
        return None

    result = normalise_trade_timestamp(value)
    # If normalization failed but input was a string, pass through unchanged
    if not result and isinstance(value, str):
        return value
    return result if result else None


def select_timestamp_value(market_data: Dict[str, Any], fields: List[str]) -> Optional[object]:
    """
    Select the first non-empty timestamp value from a list of field names.

    Args:
        market_data: Market metadata dictionary
        fields: List of field names to check in order

    Returns:
        First non-empty value found, or None
    """
    for field in fields:
        value = market_data.get(field)
        if value not in (None, "", 0):
            return value
    return None
