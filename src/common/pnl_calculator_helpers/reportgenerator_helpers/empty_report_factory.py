"""
Empty report factory for zero-trade scenarios.

Creates empty PnL reports when no trades are found.
"""

from datetime import date

from ...data_models.trade_record import PnLReport
from ...time_utils import get_timezone_aware_date, load_configured_timezone


class EmptyReportFactory:
    """Factory for creating empty PnL reports."""

    def __init__(self):
        self.timezone = load_configured_timezone()

    def create_empty_report(self, start_date: date, end_date: date) -> PnLReport:
        """
        Create an empty P&L report for when no trades are found.

        Args:
            start_date: Start date for report
            end_date: End date for report

        Returns:
            Empty PnL report with zero values
        """
        return PnLReport(
            report_date=get_timezone_aware_date(self.timezone),
            start_date=start_date,
            end_date=end_date,
            total_trades=0,
            total_cost_cents=0,
            total_pnl_cents=0,
            win_rate=0.0,
            by_weather_station={},
            by_rule={},
        )
