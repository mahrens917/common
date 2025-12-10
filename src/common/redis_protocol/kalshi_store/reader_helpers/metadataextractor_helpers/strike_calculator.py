"""
Strike calculation helpers.

Delegates to common.strike_helpers for all strike calculations.
"""

from typing import Any, Optional

from common.strike_helpers import (
    calculate_strike_value,
    parse_strike_bounds,
)


def parse_strike_values(
    floor_strike: Any, cap_strike: Any
) -> tuple[Optional[float], Optional[float]]:
    """
    Parse floor and cap strike values.

    Delegates to common.strike_helpers.parse_strike_bounds.

    Args:
        floor_strike: Raw floor strike value
        cap_strike: Raw cap strike value

    Returns:
        Tuple of (floor_value, cap_value)
    """
    return parse_strike_bounds(floor_strike, cap_strike)


__all__ = ["calculate_strike_value", "parse_strike_values"]
