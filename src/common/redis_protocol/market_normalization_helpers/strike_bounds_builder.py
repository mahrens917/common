"""Helpers for building strike bounds."""

from typing import Optional, Tuple


def determine_keyword_type(tokens: list) -> Optional[str]:
    """Determine strike keyword type from ticker tokens."""
    if "BETWEEN" in tokens:
        return "between"
    elif any(token in {"LESS", "BELOW"} for token in tokens):
        return "less"
    elif any(token in {"GREATER", "ABOVE"} for token in tokens):
        return "greater"
    return None


def apply_prefix_bounds(
    prefix: str,
    strike_type: str,
    strike_value: float,
    floor_strike: Optional[float],
    cap_strike: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:
    """Apply strike bounds based on prefix character."""
    if prefix.upper() == "B":
        cap_strike = strike_value
    elif prefix.upper() == "T":
        floor_strike = strike_value
    elif strike_type == "greater" and floor_strike is None:
        floor_strike = strike_value

    return floor_strike, cap_strike


def finalize_bounds(
    strike_type: str,
    strike_value: float,
    floor_strike: Optional[float],
    cap_strike: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:
    """Finalize strike bounds for non-BETWEEN types."""
    if strike_type == "less" and cap_strike is None:
        cap_strike = strike_value
    if strike_type == "greater" and floor_strike is None:
        floor_strike = strike_value

    return floor_strike, cap_strike
