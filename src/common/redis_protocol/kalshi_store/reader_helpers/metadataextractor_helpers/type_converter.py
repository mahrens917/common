"""
Type Converter and Strike Resolver - Handle type conversions, normalization, and strike resolution.

Converts values to strings, normalizes Redis hash responses, timestamps,
and resolves strike prices from metadata.
"""

from typing import Any, Callable, Dict, Optional

from common.strike_helpers import calculate_strike_value, parse_strike_bounds

from ...utils_coercion import string_or_default


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


def resolve_market_strike(metadata: Dict[str, Any], string_converter: Callable[[Any], Any]) -> Optional[float]:
    """
    Resolve strike from metadata payload.

    Args:
        metadata: Market metadata dictionary
        string_converter: Function to convert values to strings

    Returns:
        Calculated strike value or None if cannot be determined
    """
    strike_type_raw = metadata.get("strike_type")
    if strike_type_raw is None:
        return None
    strike_type = string_converter(strike_type_raw).lower()
    floor_value, cap_value = parse_strike_bounds(metadata.get("floor_strike"), metadata.get("cap_strike"))
    strike_value = calculate_strike_value(strike_type, floor_value, cap_value)
    if strike_value is not None:
        return strike_value
    return floor_value if floor_value is not None else cap_value
