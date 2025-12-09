"""Liquidity validation utilities."""

from typing import Any, Optional


class LiquidityValidator:
    """Validates liquidity levels."""

    @staticmethod
    def validate_sizes(
        bid_size: Any,
        ask_size: Any,
        min_liquidity: float,
    ) -> Optional[str]:
        """
        Validate bid/ask sizes.

        Args:
            bid_size: Bid size
            ask_size: Ask size
            min_liquidity: Minimum required liquidity

        Returns:
            Failure reason or None if valid
        """
        if bid_size is None or bid_size <= min_liquidity:
            return "missing_liquidity"

        if ask_size is None or ask_size <= min_liquidity:
            return "missing_liquidity"

        return None
