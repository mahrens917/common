"""
Core PnL calculation logic for individual trades and trade lists.

Provides basic PnL computation using current market values.
"""

import logging
from typing import List

from ..data_models.trade_record import TradeRecord

logger = logging.getLogger(__name__)


class PnLCalculationEngine:
    """Handles PnL calculations for individual trades and collections."""

    @staticmethod
    async def calculate_unrealized_pnl(trades: List[TradeRecord]) -> int:
        """
        Calculate total unrealized P&L for a list of trades using current market prices.

        Args:
            trades: List of trade records

        Returns:
            Total unrealized P&L in cents
        """
        total_pnl_cents = 0

        for trade in trades:
            # FAIL-FAST: If any trade can't calculate P&L, the entire calculation should fail
            # This ensures data integrity and forces fixing missing market price data
            total_pnl_cents += trade.calculate_current_pnl_cents()

        return total_pnl_cents

    @staticmethod
    def calculate_total_cost(trades: List[TradeRecord]) -> int:
        """
        Calculate total cost for a list of trades.

        Args:
            trades: List of trade records

        Returns:
            Total cost in cents
        """
        return sum(t.cost_cents for t in trades)

    @staticmethod
    def calculate_win_rate(trades: List[TradeRecord]) -> float:
        """
        Calculate win rate for a list of trades.

        Args:
            trades: List of trade records

        Returns:
            Win rate as a float between 0.0 and 1.0
        """
        if not trades:
            return 0.0

        winning_trades = sum(1 for t in trades if t.calculate_current_pnl_cents() > 0)
        return winning_trades / len(trades)
