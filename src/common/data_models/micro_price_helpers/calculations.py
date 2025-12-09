"""Micro price calculations and intrinsic value computations.

IMPORTANT: This module delegates to the canonical implementation in
src.common.data_conversion.micro_price_helpers.metrics_calculator.MetricsCalculator

The canonical implementation is used by MicroPriceConverter, which is the
"single source of truth" for micro price conversion throughout the codebase.
"""

from src.common.data_conversion.micro_price_helpers.metrics_calculator import MetricsCalculator


class MicroPriceCalculator:
    """Performs micro price calculations and option value computations.

    Delegates to MetricsCalculator for consistency with MicroPriceConverter.
    """

    @staticmethod
    def compute_micro_price_metrics(
        best_bid: float, best_ask: float, bid_size: float, ask_size: float
    ):
        """
        Compute micro price metrics from bid/ask prices and sizes.

        Delegates to canonical MetricsCalculator implementation used by MicroPriceConverter.

        Returns:
            Tuple of (absolute_spread, relative_spread, i_raw, p_raw, g, h)
        """
        # Use canonical implementation from MetricsCalculator
        # Note: MetricsCalculator returns (s_raw, i_raw, p_raw, g, h, relative_spread)
        # We reorder to maintain this function's interface
        s_raw, i_raw, p_raw, g, h, relative_spread = MetricsCalculator.compute_micro_price_metrics(
            bid_price=best_bid,
            ask_price=best_ask,
            bid_size=bid_size,
            ask_size=ask_size,
            symbol="UNKNOWN",  # Symbol only used for error messages
        )

        # Reorder return values to match this function's original interface
        return s_raw, relative_spread, i_raw, p_raw, g, h

    @staticmethod
    def compute_intrinsic_value(option_type: str, strike: float, spot_price: float) -> float:
        """Calculate intrinsic value given spot price."""
        if option_type.lower() == "call":
            return max(0.0, spot_price - strike)
        else:  # put
            return max(0.0, strike - spot_price)

    @staticmethod
    def compute_time_value(
        option_type: str, strike: float, spot_price: float, micro_price: float
    ) -> float:
        """Calculate time value given spot price using micro price."""
        intrinsic = MicroPriceCalculator.compute_intrinsic_value(option_type, strike, spot_price)
        return max(0.0, micro_price - intrinsic)
