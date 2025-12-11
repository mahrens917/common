"""
Strike Resolver - Resolve strike prices from metadata.

Delegates to common.strike_helpers for all strike calculations.
"""

from typing import Any, Callable, Dict, Optional

from common.strike_helpers import calculate_strike_value, parse_strike_bounds

__all__ = ["StrikeResolver"]


class StrikeResolver:
    """Resolve strike prices from metadata fields."""

    @staticmethod
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

    @staticmethod
    def resolve_strike_from_combined(combined: Dict[str, Any], string_converter: Callable[[Any], Any]) -> Optional[float]:
        """
        Resolve strike from combined metadata/hash snapshots.

        Args:
            combined: Combined metadata dictionary
            string_converter: Function to convert values to strings

        Returns:
            Calculated strike value or None if cannot be determined
        """
        return StrikeResolver.resolve_market_strike(combined, string_converter)
