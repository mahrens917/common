"""Micro price metrics calculation."""

import logging
import math

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculates micro price metrics from bid/ask data."""

    @staticmethod
    def compute_micro_price_metrics(
        bid_price: float, ask_price: float, bid_size: float, ask_size: float, symbol: str
    ) -> tuple[float, float, float, float, float, float]:
        """Compute micro price metrics from bid/ask data."""
        s_raw = ask_price - bid_price
        total_volume = bid_size + ask_size
        if total_volume <= 0:
            raise ValueError(
                "FAIL-FAST: Zero total volume (bid_size={bid}, ask_size={ask}) for instrument {symbol}. "
                "Cannot calculate micro price with non-positive volume - all volume data must be positive real market data.".format(
                    bid=bid_size, ask=ask_size, symbol=symbol
                )
            )

        i_raw = bid_size / total_volume
        p_raw = (bid_price * ask_size + ask_price * bid_size) / total_volume

        g = math.log(s_raw) if s_raw > 0 else math.log(1e-10)

        if i_raw <= 0:
            i_raw = 1e-10
        elif i_raw >= 1:
            i_raw = 1 - 1e-10
        h = math.log(i_raw / (1 - i_raw))

        relative_spread = s_raw / p_raw if p_raw > 0 else float("inf")
        return s_raw, i_raw, p_raw, g, h, relative_spread
