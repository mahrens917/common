"""Fee calculation for Kalshi orders."""

import importlib
import logging

logger = logging.getLogger(__name__)


class FeeCalculator:
    """Calculate fees for Kalshi orders."""

    @staticmethod
    async def calculate_order_fees(market_ticker: str, quantity: int, price_cents: int) -> int:
        """Calculate fees for a proposed order."""
        try:
            fee_func = getattr(importlib.import_module("common.kalshi_trading_client"), "calculate_fees")
        except AttributeError:
            from ....kalshi_fees import calculate_fees as fee_func

        try:
            return fee_func(quantity, price_cents, market_ticker)
        except (ValueError, TypeError, RuntimeError, OverflowError) as exc:
            logger.exception(
                "Failed to calculate fees for %s (%s)",
                market_ticker,
                type(exc).__name__,
            )
            raise ValueError(f"Cannot calculate fees for {market_ticker}") from exc


# Expose canonical entrypoint for reuse across client helpers.
calculate_order_fees = FeeCalculator.calculate_order_fees

__all__ = ["FeeCalculator", "calculate_order_fees"]
