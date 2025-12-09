"""Price validation utilities."""

from typing import Any, Optional


class PriceValidator:
    """Validates price data quality."""

    @staticmethod
    def validate_quotes(
        best_bid: Any,
        best_ask: Any,
        max_relative_spread: float,
    ) -> Optional[str]:
        """
        Validate bid/ask quotes.

        Args:
            best_bid: Best bid price
            best_ask: Best ask price
            max_relative_spread: Maximum allowed relative spread

        Returns:
            Failure reason or None if valid
        """
        if best_bid is None or best_ask is None:
            return "missing_quotes"

        if best_bid <= 0 or best_ask <= 0:
            return "invalid_price"

        if best_ask <= best_bid:
            return "invalid_spread"

        # Check relative spread
        mid_price = 0.5 * (best_bid + best_ask)
        spread = best_ask - best_bid

        if mid_price <= 0:
            return "invalid_price"

        relative_spread = spread / mid_price
        if relative_spread > max_relative_spread:
            return "wide_spread"

        return None
