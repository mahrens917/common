"""
Report generator for Kalshi trading P&L reports.

This module generates formatted reports for Telegram delivery with
comprehensive breakdowns by weather station, time, and trading rules.

Refactored to use composition with focused helper coordinators.
"""

import logging
from datetime import date
from typing import Any, Dict

from .exceptions import ConfigurationError
from .pnl_calculator import PnLCalculator
from .report_generator_helpers import CoordinatorFactory, ReportDelegator
from .time_utils import load_configured_timezone

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates formatted P&L reports for Telegram delivery.

    Creates human-readable reports with proper formatting and emoji
    indicators for easy consumption via Telegram bot.

    Refactored to use composition with focused helper coordinators.
    """

    def __init__(self, pnl_calculator: PnLCalculator):
        """
        Initialize report generator.

        Args:
            pnl_calculator: P&L calculator for data generation
        """
        self.pnl_calculator = pnl_calculator
        self.logger = logger
        self.timezone = self._load_timezone_config()

        # Create all coordinators via factory
        (
            self.message_formatter,
            report_coordinator,
            summary_builder,
            unified_builder,
        ) = CoordinatorFactory.create_coordinators(pnl_calculator, self.timezone)

        # Create delegator to handle report generation with error handling
        self.delegator = ReportDelegator(report_coordinator, summary_builder, unified_builder)

    def _load_timezone_config(self) -> str:
        """Load timezone configuration using the shared config loader."""
        try:
            return load_configured_timezone()
        except RuntimeError as exc:
            raise ConfigurationError("Failed to load reporting timezone configuration") from exc

    async def generate_daily_report(self, trade_date: date) -> str:
        """Generate daily P&L report for a specific date."""
        return await self.delegator.generate_daily_report(trade_date)

    async def generate_historical_report(self, start_date: date, end_date: date) -> str:
        """Generate historical P&L report for a date range."""
        return await self.delegator.generate_historical_report(start_date, end_date)

    async def generate_current_day_report(self) -> str:
        """Generate report for current day including unrealized P&L."""
        return await self.delegator.generate_current_day_report()

    async def generate_settlement_notification(
        self, trade_date: date, settled_markets: list
    ) -> str:
        """Generate notification when markets settle."""
        daily_report = await self.generate_daily_report(trade_date)
        return await self.delegator.generate_settlement_notification(
            trade_date, settled_markets, daily_report
        )

    def format_error_message(self, error_msg: str) -> str:
        """Format error message for Telegram display."""
        return self.message_formatter.format_error_message(error_msg)

    def format_no_data_message(self, date_range: str) -> str:
        """Format message when no trade data is found."""
        return self.message_formatter.format_no_data_message(date_range)

    async def generate_summary_stats(self, days_back: int = 30) -> str:
        """Generate summary statistics for the last N days."""
        return await self.delegator.generate_summary_stats(days_back)

    async def generate_unified_pnl_report(self) -> str:
        """Generate unified P&L report with today, yesterday, 7-day, and 30-day."""
        return await self.delegator.generate_unified_pnl_report()

    async def generate_unified_pnl_data(self) -> Dict[str, Any]:
        """Generate unified P&L data for chart generation."""
        return await self.delegator.generate_unified_pnl_data()
