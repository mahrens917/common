"""
Type Converter - Handle type conversions and normalization

Converts values to strings, normalizes Redis hash responses, and timestamps.
"""

from typing import Any, Dict, Optional

from common.redis_protocol.kalshi_store.utils_coercion import string_or_default as _string_or_default


def string_or_default(value: Any, fill_value: str = "") -> str:
    """
    Convert value to string or return fill value

    Args:
        value: Value to convert
        fill_value: Fill value if conversion fails

    Returns:
        String representation or fill value
    """
    return _string_or_default(value, fill_value)


def normalize_hash(raw_hash: Dict[Any, Any]) -> Dict[str, Any]:
    """
    Convert Redis hash responses to a str-keyed dictionary.

    Args:
        raw_hash: Raw Redis hash with potentially byte keys/values

    Returns:
        Normalized dictionary with string keys
    """
    normalised: Dict[str, Any] = {}
    for key, value in raw_hash.items():
        if isinstance(key, bytes):
            key = key.decode("utf-8", "ignore")
        if isinstance(value, bytes):
            value = value.decode("utf-8", "ignore")
        normalised[str(key)] = value
    return normalised


def normalize_timestamp(timestamp: Any) -> Optional[str]:
    """Normalize timestamp to string format via canonical implementation."""
    from common.redis_protocol.kalshi_store.metadata_helpers.timestamp_normalization import normalize_timestamp as _canonical

    return _canonical(timestamp)
