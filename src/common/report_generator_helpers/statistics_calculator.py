"""
Statistics calculator for P&L reports.

Calculates ROI, averages, and best performers from report data.
"""

from typing import Dict

from ..data_models.trade_record import PnLBreakdown


class StatisticsCalculator:
    """Calculates statistics from P&L data."""

    @staticmethod
    def calculate_roi(pnl_dollars: float, cost_dollars: float) -> float:
        """
        Calculate ROI percentage.

        Args:
            pnl_dollars: P&L in dollars
            cost_dollars: Cost basis in dollars

        Returns:
            ROI as percentage (0.0 if cost is zero)
        """
        if cost_dollars > 0:
            return (pnl_dollars / cost_dollars) * 100
        return 0.0

    @staticmethod
    def calculate_average_pnl_per_trade(pnl_dollars: float, trade_count: int) -> float:
        """
        Calculate average P&L per trade.

        Args:
            pnl_dollars: Total P&L in dollars
            trade_count: Number of trades

        Returns:
            Average P&L per trade (0.0 if no trades)
        """
        if trade_count > 0:
            return pnl_dollars / trade_count
        return 0.0

    @staticmethod
    def get_best_performer(breakdown: Dict[str, PnLBreakdown]) -> str:
        """
        Get the best performing category from a breakdown.

        Args:
            breakdown: Breakdown dictionary

        Returns:
            Best performer description
        """
        if not breakdown:
            return "N/A"

        # Find category with highest P&L
        best_category = max(breakdown.items(), key=lambda x: x[1].pnl_cents)
        category_name = best_category[0]
        category_pnl = best_category[1].pnl_cents / 100

        return f"{category_name} (${category_pnl:+.2f})"

    @staticmethod
    def calculate_win_rate(trades) -> float:
        """
        Calculate win rate from trade list.

        Args:
            trades: List of trade records

        Returns:
            Win rate as float (0.0-1.0)
        """
        if not trades:
            return 0.0

        winning_trades = sum(1 for t in trades if t.is_winning_trade())
        return winning_trades / len(trades)
