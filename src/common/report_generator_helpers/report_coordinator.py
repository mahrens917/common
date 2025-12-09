"""
Report coordinator for basic report types.

Handles generation of daily, historical, and current day reports.
"""

import logging
from datetime import date

from ..pnl_calculator import PnLCalculator
from ..time_utils import get_current_date_in_timezone, get_current_utc, get_timezone_aware_date
from .basic_pnl_formatter import BasicPnLFormatter
from .current_day_formatter import CurrentDayFormatter

logger = logging.getLogger(__name__)


class ReportCoordinator:
    """Coordinates basic report generation (daily, historical, current day)."""

    def __init__(
        self,
        pnl_calculator: PnLCalculator,
        basic_formatter: BasicPnLFormatter,
        current_day_formatter: CurrentDayFormatter,
        timezone: str,
    ):
        """
        Initialize report coordinator.

        Args:
            pnl_calculator: P&L calculator for data generation
            basic_formatter: Formatter for basic reports
            current_day_formatter: Formatter for current day reports
            timezone: Configured timezone for date calculations
        """
        self.pnl_calculator = pnl_calculator
        self.basic_formatter = basic_formatter
        self.current_day_formatter = current_day_formatter
        self.timezone = timezone
        self.logger = logger

    async def generate_daily_report(self, trade_date: date) -> str:
        """
        Generate daily P&L report for a specific date.

        Args:
            trade_date: Date to generate report for

        Returns:
            Formatted report string for Telegram
        """
        report = await self.pnl_calculator.generate_aggregated_report(trade_date, trade_date)
        return self.basic_formatter.format_pnl_report(
            report, f"Daily Report - {trade_date.strftime('%B %d, %Y')}"
        )

    async def generate_historical_report(self, start_date: date, end_date: date) -> str:
        """
        Generate historical P&L report for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Formatted report string for Telegram
        """
        report = await self.pnl_calculator.generate_aggregated_report(start_date, end_date)
        date_range = f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}"
        return self.basic_formatter.format_pnl_report(report, f"Historical Report ({date_range})")

    async def generate_current_day_report(self) -> str:
        """
        Generate report for current day including unrealized P&L.

        Returns:
            Formatted report string for Telegram
        """
        # Use configured timezone instead of UTC
        if self.timezone == "UTC":
            today = get_current_utc().date()
        else:
            today = get_current_date_in_timezone(self.timezone).date()

        report = await self.pnl_calculator.generate_aggregated_report(today, today)
        unrealized_pnl = await self.pnl_calculator.get_current_day_unrealized_pnl()

        date_str = get_timezone_aware_date(self.timezone).strftime("%B %d, %Y")
        return self.current_day_formatter.format_current_day_report(
            report, unrealized_pnl, date_str
        )
