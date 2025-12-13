"""
Consolidated strike value parsing, extraction, and validation utilities.

This module provides canonical strike handling functions for all strike types:
- Numeric (single value)
- Range (low-high)
- Greater-than (>value or floor_strike for 'greater' type)
- Less-than (<value or cap_strike for 'less' type)
- Between (floor_strike to cap_strike for 'between' type)

All strike-related code should import from this module to avoid duplication.
"""

import logging
from typing import Any, Dict, Mapping, Optional, Tuple

import numpy as np

from common.truthy import pick_if

from .strike_helpers_utils import (
    compute_representative_strike,
    decode_redis_key,
    decode_value,
    extract_between_bounds,
    extract_strike_from_key,
    format_strike_display,
    parse_strike_segment,
    resolve_strike_type,
    resolve_strike_type_from_prefix,
    to_float,
)

logger = logging.getLogger(__name__)


# Constants
_CONST_5 = 5


def parse_strike_value(strike_str: str) -> Optional[float]:
    """
    Parse single strike value from string.

    Args:
        strike_str: Strike string (numeric value)

    Returns:
        Strike as float or None if parsing fails
    """
    try:
        return float(strike_str)
    except (ValueError, TypeError) as parse_error:  # policy_guard: allow-silent-handler
        logger.debug("Could not parse strike value '%s': %s", strike_str, parse_error)
        return None


def parse_strike_bounds(floor_strike: Any, cap_strike: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse floor and cap strike values from any type.

    Args:
        floor_strike: Raw floor strike value (can be None, str, bytes, int, float)
        cap_strike: Raw cap strike value (can be None, str, bytes, int, float)

    Returns:
        Tuple of (floor_value, cap_value) where None indicates missing, empty,
        or unparsable values.
    """

    def _parse_optional(value: Any) -> Optional[float]:
        if value in (None, "", b""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
            logger.debug("Could not parse strike value %r: %s", value, exc)
            return None

    floor_value = _parse_optional(floor_strike)
    cap_value = _parse_optional(cap_strike)
    return floor_value, cap_value


def calculate_strike_value(
    strike_type: str,
    floor_value: Optional[float],
    cap_value: Optional[float],
) -> Optional[float]:
    """
    Calculate representative strike based on type and floor/cap values.

    For 'between' type: returns midpoint of floor and cap
    For 'greater' type: returns floor value
    For 'less' type: returns cap value

    Args:
        strike_type: Type of strike ('between', 'greater', 'less')
        floor_value: Floor strike value
        cap_value: Cap strike value

    Returns:
        Calculated representative strike or None if cannot be determined
    """
    strike_type_lower = pick_if(strike_type, lambda: strike_type.lower(), lambda: "")

    if strike_type_lower == "between" and floor_value is not None and cap_value is not None:
        return (floor_value + cap_value) / 2
    if strike_type_lower == "greater" and floor_value is not None:
        return floor_value
    if strike_type_lower == "less" and cap_value is not None:
        return cap_value
    return None


def calculate_strike_bounds(strike_type: str, strike_price: float) -> Tuple[str, float, float]:
    """
    Return canonical floor and cap strikes for a pricing mix based on type.

    Args:
        strike_type: Kalshi strike type ('greater', 'less', 'between')
        strike_price: Display strike extracted from the ticker

    Returns:
        Tuple containing the normalized strike type, floor strike, and cap strike
    """
    strike_type_lower = pick_if(strike_type, lambda: strike_type.lower(), lambda: "")

    if strike_type_lower == "greater":
        return "greater", strike_price, float("inf")

    if strike_type_lower == "less":
        return "less", 0.0, strike_price

    if strike_type_lower == "between":
        margin = strike_price * 0.1
        return "between", strike_price - margin, strike_price + margin

    # Default to greater when type is unknown
    return "greater", strike_price, float("inf")


def resolve_strike_from_metadata(metadata: Dict[str, Any]) -> Optional[float]:
    """
    Calculate representative strike from floor/cap/strike_type metadata.

    Args:
        metadata: Market metadata dictionary containing strike_type, floor_strike, cap_strike

    Returns:
        Calculated strike value or None if cannot be determined
    """
    strike_type = metadata.get("strike_type")
    if strike_type is None:
        return None

    # Convert to string if needed
    if isinstance(strike_type, bytes):
        try:
            strike_type = strike_type.decode("utf-8")
        except UnicodeDecodeError:  # policy_guard: allow-silent-handler
            return None
    strike_type = str(strike_type)

    floor_value, cap_value = parse_strike_bounds(metadata.get("floor_strike"), metadata.get("cap_strike"))
    return calculate_strike_value(strike_type, floor_value, cap_value)


def check_strike_in_range(strike_str: str, strike_low: float, strike_high: float) -> bool:
    """
    Check if strike falls within the specified range.

    Handles multiple strike formats:
    - Single value: "50000"
    - Range: "50000-60000"
    - Greater-than: ">60000"
    - Less-than: "<60000"

    Args:
        strike_str: Strike string from Redis key or market data
        strike_low: Lower bound of target range
        strike_high: Upper bound of target range

    Returns:
        True if strike overlaps with target range, False otherwise
    """
    try:
        if "-" in strike_str and not strike_str.startswith("-"):
            # Range format: "50000-60000"
            range_low_str, range_high_str = strike_str.split("-", 1)
            range_low = float(range_low_str)
            range_high = float(range_high_str)
            # Check for overlap: range intersects target if not (range_high < low OR range_low > high)
            return not (range_high < strike_low or range_low > strike_high)

        if ">" in strike_str:
            # Greater-than format: ">60000"
            threshold = float(strike_str[1:])
            # Include if threshold is within or below target range
            return threshold <= strike_high

        if "<" in strike_str:
            # Less-than format: "<60000"
            threshold = float(strike_str[1:])
            # Include if threshold is within or above target range
            return threshold >= strike_low

        # Single value format: "50000"
        strike_value = float(strike_str)
    except (ValueError, TypeError) as parse_error:  # policy_guard: allow-silent-handler
        logger.debug("Could not parse strike value from '%s': %s", strike_str, parse_error)
        return False
    else:
        return strike_low <= strike_value <= strike_high


def extract_strike_parameters(market_data: Optional[Dict[str, Any]], strike_type: Optional[str]) -> Tuple[str, float, float]:
    """
    Extract strike parameters based on market type and available data.

    Args:
        market_data: Market data dictionary from Redis
        strike_type: Strike type attribute from market

    Returns:
        Tuple of (strike_type, floor_strike, cap_strike)
        - strike_type: 'greater', 'less', or 'between'
        - floor_strike: Lower bound for 'between', strike for 'greater', 0 for 'less'
        - cap_strike: Upper bound for 'between', infinity for 'greater', strike for 'less'

    Raises:
        ValueError: If required strike data is missing or strike_type is unknown
    """
    if market_data is None:
        market_data = {}
    strike_type = resolve_strike_type(market_data, strike_type)

    floor_strike_value = market_data.get("floor_strike")
    cap_strike_value = market_data.get("cap_strike")

    if strike_type == "greater":
        if floor_strike_value is None:
            raise ValueError("Greater market missing required floor_strike from Redis")
        return strike_type, float(floor_strike_value), float("inf")

    if strike_type == "less":
        if cap_strike_value is None:
            raise ValueError("Less market missing required cap_strike from Redis")
        return strike_type, 0.0, float(cap_strike_value)

    if strike_type == "between":
        if floor_strike_value is None or cap_strike_value is None:
            raise ValueError("Between market missing required floor_strike or cap_strike from Redis")
        return strike_type, float(floor_strike_value), float(cap_strike_value)

    raise ValueError(f"Unknown strike_type '{strike_type}' - must be 'greater', 'less', or 'between'")


def validate_strike_type(metadata: Mapping[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate strike_type field is present and recognized.

    Args:
        metadata: Market metadata dictionary

    Returns:
        Tuple of (is_valid, error_reason, strike_type_lower)
    """
    strike_type = decode_value(metadata.get("strike_type"))
    if not strike_type:
        return False, "unknown_strike_type", None

    return True, None, str(strike_type).lower()


def compute_strike_value(
    strike_type_lower: str, metadata: Mapping[str, Any]
) -> Tuple[bool, Optional[str], Optional[float], Optional[float], Optional[float]]:
    """
    Compute strike value based on strike type with validation.

    Args:
        strike_type_lower: Strike type in lowercase ('between', 'greater', 'less')
        metadata: Market metadata dictionary

    Returns:
        Tuple of (is_valid, error_reason, strike, floor_strike, cap_strike)
    """
    floor_strike = to_float(metadata.get("floor_strike"))
    cap_strike = to_float(metadata.get("cap_strike"))

    handler = _STRIKE_HANDLERS.get(strike_type_lower)
    if not handler:
        reason = "unknown_strike_type"
        strike = None
    else:
        strike, reason = handler(floor_strike, cap_strike)

    is_valid = strike is not None and reason is None
    return is_valid, reason, strike, floor_strike, cap_strike


def _handle_between(floor_strike: Optional[float], cap_strike: Optional[float]) -> Tuple[Optional[float], Optional[str]]:
    if floor_strike is None or cap_strike is None:
        return None, "between_missing_bounds"
    return float(np.mean([floor_strike, cap_strike])), None


def _handle_greater(floor_strike: Optional[float], _: Optional[float]) -> Tuple[Optional[float], Optional[str]]:
    if floor_strike is None:
        _none_guard_value = None, "greater_missing_floor"
        return _none_guard_value
    return floor_strike, None


def _handle_less(_: Optional[float], cap_strike: Optional[float]) -> Tuple[Optional[float], Optional[str]]:
    if cap_strike is None:
        _none_guard_value = None, "less_missing_cap"
        return _none_guard_value
    return cap_strike, None


_STRIKE_HANDLERS = {
    "between": _handle_between,
    "greater": _handle_greater,
    "less": _handle_less,
}


__all__ = [
    "parse_strike_value",
    "parse_strike_bounds",
    "calculate_strike_value",
    "calculate_strike_bounds",
    "resolve_strike_from_metadata",
    "check_strike_in_range",
    "extract_strike_parameters",
    "validate_strike_type",
    "compute_strike_value",
    "parse_strike_segment",
    "resolve_strike_type_from_prefix",
    "extract_between_bounds",
    "compute_representative_strike",
    "decode_redis_key",
    "extract_strike_from_key",
    "format_strike_display",
]
