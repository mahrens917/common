"""
Summary report builder for specialized report types.

Handles generation of summary statistics and settlement notifications.
"""

import logging
from datetime import date, timedelta

from ..pnl_calculator import PnLCalculator
from ..time_utils import get_timezone_aware_date
from .statistics_calculator import StatisticsCalculator

logger = logging.getLogger(__name__)


class SummaryReportBuilder:
    """Builds summary statistics and settlement notifications."""

    def __init__(
        self,
        pnl_calculator: PnLCalculator,
        stats_calculator: StatisticsCalculator,
        timezone: str,
    ):
        """
        Initialize summary report builder.

        Args:
            pnl_calculator: P&L calculator for data generation
            stats_calculator: Calculator for statistics
            timezone: Configured timezone for date calculations
        """
        self.pnl_calculator = pnl_calculator
        self.stats_calculator = stats_calculator
        self.timezone = timezone
        self.logger = logger

    async def generate_summary_stats(self, days_back: int = 30) -> str:
        """
        Generate summary statistics for the last N days.

        Args:
            days_back: Number of days to look back

        Returns:
            Formatted summary statistics
        """
        end_date = get_timezone_aware_date(self.timezone)
        start_date = end_date - timedelta(days=days_back)

        report = await self.pnl_calculator.generate_aggregated_report(start_date, end_date)

        # Calculate metrics
        total_pnl_dollars = report.total_pnl_cents / 100
        total_cost_dollars = report.total_cost_cents / 100

        roi_percent = self.stats_calculator.calculate_roi(total_pnl_dollars, total_cost_dollars)
        avg_pnl_per_trade = self.stats_calculator.calculate_average_pnl_per_trade(
            total_pnl_dollars, report.total_trades
        )

        lines = [
            f"📈 **{days_back}-Day Summary**",
            "",
            f"💰 Total P&L: ${total_pnl_dollars:,.2f}",
            f"📊 ROI: {roi_percent:+.1f}%",
            f"📈 Total Trades: {report.total_trades}",
            f"🎯 Win Rate: {report.win_rate:.1%}",
            f"💵 Avg P&L/Trade: ${avg_pnl_per_trade:,.2f}",
            "",
            f"🏆 Best Station: {self.stats_calculator.get_best_performer(report.by_weather_station)}",
            f"⭐ Best Rule: {self.stats_calculator.get_best_performer(report.by_rule)}",
        ]

        return "\n".join(lines)

    async def generate_settlement_notification(
        self, trade_date: date, settled_markets: list, daily_report: str
    ) -> str:
        """
        Generate notification when markets settle.

        Args:
            trade_date: Date of settled trades
            settled_markets: List of market tickers that settled
            daily_report: Pre-generated daily report string

        Returns:
            Formatted notification string
        """
        settlement_header = [
            f"🔔 **Settlement Alert - {trade_date.strftime('%B %d, %Y')}**",
            f"✅ {len(settled_markets)} markets have settled",
            "",
            "📊 **Final Results:**",
            "",
        ]

        return "\n".join(settlement_header) + daily_report
