from __future__ import annotations

"""Helper for accumulating strike values"""


from typing import Optional


class StrikeAccumulator:
    """Accumulates strike values based on strike type"""

    def accumulate_strike_values(
        self,
        strike_type: str,
        floor_strike: Optional[float],
        cap_strike: Optional[float],
        strikes: set[float],
    ) -> None:
        """
        Add strike values to set based on strike type

        Args:
            strike_type: Type of strike (greater, less, between, or other)
            floor_strike: Floor strike value
            cap_strike: Cap strike value
            strikes: Set to add strikes to (mutated in place)
        """
        if strike_type == "greater":
            self._add_floor_strike(floor_strike, strikes)
            return

        if strike_type == "less":
            self._add_cap_strike(cap_strike, strikes)
            return

        if strike_type == "between":
            self._add_both_strikes(floor_strike, cap_strike, strikes)
            return

        self._add_both_strikes(floor_strike, cap_strike, strikes)

    @staticmethod
    def _add_floor_strike(floor_strike: Optional[float], strikes: set[float]) -> None:
        """Add floor strike if present."""
        if floor_strike is not None:
            strikes.add(floor_strike)

    @staticmethod
    def _add_cap_strike(cap_strike: Optional[float], strikes: set[float]) -> None:
        """Add cap strike if present."""
        if cap_strike is not None:
            strikes.add(cap_strike)

    @staticmethod
    def _add_both_strikes(floor_strike: Optional[float], cap_strike: Optional[float], strikes: set[float]) -> None:
        """Add both floor and cap strikes if present."""
        if floor_strike is not None:
            strikes.add(floor_strike)
        if cap_strike is not None:
            strikes.add(cap_strike)
