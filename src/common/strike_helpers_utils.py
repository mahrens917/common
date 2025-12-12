"""Helper utilities split from :mod:`common.strike_helpers`."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CONST_5 = 5


def parse_strike_segment(strike_segment: str) -> Tuple[str, str]:
    """
    Parse strike segment into prefix and value string.

    Used for parsing market ticker segments with prefix indicators (B/T/M).
    """
    if not strike_segment:
        return "", ""

    prefix = strike_segment[0]
    value_str = strike_segment[1:] if prefix.isalpha() else strike_segment
    return prefix, value_str


def resolve_strike_type_from_prefix(prefix: str, keyword_type: Optional[str]) -> Tuple[str, Optional[float], Optional[float]]:
    strike_type = keyword_type or "greater"
    floor_strike: Optional[float] = None
    cap_strike: Optional[float] = None

    prefix_upper = prefix.upper()
    if prefix_upper == "B":
        strike_type = "less"
    elif prefix_upper == "T":
        strike_type = "greater"
    elif prefix_upper == "M":
        strike_type = "between"
    elif keyword_type is not None:
        strike_type = keyword_type

    return strike_type, floor_strike, cap_strike


def extract_between_bounds(tokens: List[str]) -> Tuple[Optional[float], Optional[float]]:
    def _parse_float(segment: Optional[str]) -> Optional[float]:
        if segment is None:
            return None
        try:
            return float(segment)
        except (TypeError, ValueError):  # policy_guard: allow-silent-handler
            return None

    try:
        idx = tokens.index("BETWEEN")
    except ValueError:  # policy_guard: allow-silent-handler
        return None, None

    floor_strike = _parse_float(tokens[idx + 1] if idx + 1 < len(tokens) else None)
    cap_candidate = tokens[idx + 2] if idx + 2 < len(tokens) else None
    cap_strike = _parse_float(cap_candidate)

    return floor_strike, cap_strike


def compute_representative_strike(cap_strike: Optional[float], floor_strike: Optional[float], strike_value: float) -> float:
    if cap_strike is not None:
        return cap_strike
    if floor_strike is not None:
        return floor_strike
    return strike_value


def decode_redis_key(key: bytes | str) -> Optional[str]:
    if isinstance(key, bytes):
        try:
            return key.decode("utf-8")
        except UnicodeDecodeError as decode_error:  # policy_guard: allow-silent-handler
            logger.debug("Could not decode strike key %s: %s", key, decode_error)
            return None
    return str(key)


def extract_strike_from_key(key_str: str) -> Optional[str]:
    parts = key_str.split(":")
    if len(parts) < _CONST_5:
        logger.debug("Skipping malformed probability key %s", key_str)
        return None
    return parts[4]


def format_strike_display(strike_type: str, cap: Optional[float], floor: Optional[float]) -> str:
    if strike_type == "between":
        return f"{floor}°F-{cap}°F range"
    if strike_type == "less":
        return f"cap {cap}°F"
    if strike_type == "greater":
        return f"floor {floor}°F"
    return "unknown strikes"


def resolve_strike_type(market_data: Dict[str, Any], strike_type: Optional[str]) -> str:
    if strike_type:
        return strike_type
    raw_strike_type = market_data.get("strike_type")
    return str(raw_strike_type) if raw_strike_type is not None else "unknown"


def decode_value(value: Any) -> Any:
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:  # policy_guard: allow-silent-handler
            return None
    return value


def to_float(value: Any) -> Optional[float]:
    if value in (None, "", b""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):  # policy_guard: allow-silent-handler
        return None
