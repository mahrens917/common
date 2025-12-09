"""Strike field derivation logic."""

from typing import Optional, Tuple

from ...strike_helpers import (
    compute_representative_strike,
    extract_between_bounds,
)

StrikeFields = Optional[Tuple[str, Optional[float], Optional[float], float]]


class StrikeDerivation:
    """Derives strike fields from Kalshi ticker format."""

    @staticmethod
    def determine_keyword_type(tokens: list) -> Optional[str]:
        """Determine keyword type from ticker tokens."""
        if "BETWEEN" in tokens:
            return "between"
        if any(token in {"LESS", "BELOW"} for token in tokens):
            return "less"
        if any(token in {"GREATER", "ABOVE"} for token in tokens):
            return "greater"
        return None

    @staticmethod
    def apply_prefix_bounds(
        prefix: str,
        strike_type: str,
        strike_value: float,
        floor_strike: Optional[float],
        cap_strike: Optional[float],
    ) -> Tuple[Optional[float], Optional[float]]:
        """Apply bounds based on prefix character."""
        if prefix.upper() == "B":
            return floor_strike, strike_value
        if prefix.upper() == "T":
            return strike_value, cap_strike
        if strike_type == "greater" and floor_strike is None:
            return strike_value, cap_strike
        return floor_strike, cap_strike

    @staticmethod
    def handle_between_type(
        tokens: list,
        floor_strike: Optional[float],
        cap_strike: Optional[float],
        strike_value: float,
    ) -> StrikeFields:
        """Handle BETWEEN type strike extraction."""
        between_floor, between_cap = extract_between_bounds(tokens)
        if between_floor is not None:
            floor_strike = between_floor
        if between_cap is not None:
            cap_strike = between_cap

        representative = compute_representative_strike(cap_strike, floor_strike, strike_value)
        return "between", floor_strike, cap_strike, representative

    @staticmethod
    def finalize_bounds(
        strike_type: str,
        strike_value: float,
        floor_strike: Optional[float],
        cap_strike: Optional[float],
    ) -> Tuple[Optional[float], Optional[float]]:
        """Finalize bounds for non-BETWEEN types."""
        final_floor = floor_strike
        final_cap = cap_strike

        if strike_type == "less" and cap_strike is None:
            final_cap = strike_value
        if strike_type == "greater" and floor_strike is None:
            final_floor = strike_value

        return final_floor, final_cap
