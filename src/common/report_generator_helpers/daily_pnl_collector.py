"""Daily P&L data collector.

Collects daily P&L data series for chart generation.
"""

import logging
from datetime import date, timedelta
from typing import List, Tuple

from ..pnl_calculator import PnLCalculator

# Local constant for error handling
DATA_ACCESS_ERRORS = (KeyError, AttributeError, TypeError, ValueError)

logger = logging.getLogger(__name__)


class DailyPnLCollector:
    """Collects daily P&L data series."""

    def __init__(self, pnl_calculator: PnLCalculator):
        """
        Initialize daily P&L collector.

        Args:
            pnl_calculator: P&L calculator for data access
        """
        self.pnl_calculator = pnl_calculator

    async def get_daily_pnl_with_unrealized_percentage(
        self, start_date: date, end_date: date
    ) -> List[Tuple[date, float]]:
        """
        Get daily P&L series as percentage of money traded.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of (date, pnl_percentage) tuples
        """
        try:
            daily_pnl_percentage = []
            current_date = start_date

            while current_date <= end_date:
                # Use unified P&L calculation
                pnl_cents = await self.pnl_calculator.get_unified_pnl_for_date(current_date)

                # Get trades for cost calculation
                trades = await self.pnl_calculator.trade_store.get_trades_by_date_range(
                    current_date, current_date
                )
                day_cost_cents = sum(trade.cost_cents for trade in trades)

                # Calculate percentage return
                if day_cost_cents > 0:
                    pnl_percentage = (pnl_cents / day_cost_cents) * 100.0
                else:
                    pnl_percentage = 0.0

                daily_pnl_percentage.append((current_date, pnl_percentage))
                current_date += timedelta(days=1)

            else:
                return daily_pnl_percentage
        except DATA_ACCESS_ERRORS as exc:
            logger.error(
                "Error getting daily P&L percentage series (%s): %s",
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            raise

    async def get_daily_pnl_with_unrealized(
        self, start_date: date, end_date: date
    ) -> List[Tuple[date, int]]:
        """
        Get daily P&L series in cents.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of (date, pnl_cents) tuples
        """
        try:
            daily_pnl = []
            current_date = start_date

            while current_date <= end_date:
                # Use unified P&L calculation
                pnl_cents = await self.pnl_calculator.get_unified_pnl_for_date(current_date)
                daily_pnl.append((current_date, pnl_cents))
                current_date += timedelta(days=1)

            else:
                return daily_pnl
        except DATA_ACCESS_ERRORS as exc:
            logger.error(
                "Error getting daily P&L series (%s): %s", type(exc).__name__, exc, exc_info=True
            )
            raise
