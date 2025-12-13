"""Report delegator for handling all report generation with error handling.

Delegates to specialized coordinators and provides consistent error handling.
"""

import logging
from datetime import date
from typing import Any, Dict

from .report_coordinator import ReportCoordinator
from .summary_report_builder import SummaryReportBuilder
from .unified_report_builder import UnifiedReportBuilder

# Local constant for error handling
DATA_ACCESS_ERRORS = (KeyError, AttributeError, TypeError, ValueError)

logger = logging.getLogger(__name__)


class ReportDelegator:
    """Delegates report generation requests to specialized coordinators."""

    def __init__(
        self,
        report_coordinator: ReportCoordinator,
        summary_builder: SummaryReportBuilder,
        unified_builder: UnifiedReportBuilder,
    ):
        """Initialize report delegator with coordinators."""
        self.report_coordinator = report_coordinator
        self.summary_builder = summary_builder
        self.unified_builder = unified_builder
        self.logger = logger

    async def generate_daily_report(self, trade_date: date) -> str:
        try:
            result = await self.report_coordinator.generate_daily_report(trade_date)
            self.logger.info("Generated daily report for %s", trade_date)
        except DATA_ACCESS_ERRORS as exc:  # policy_guard: allow-silent-handler
            self.logger.error(
                "Error generating daily report for %s (%s): %s",
                trade_date,
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            return f"❌ Error generating daily report for {trade_date}"
        else:
            return result

    async def generate_historical_report(self, start_date: date, end_date: date) -> str:
        try:
            result = await self.report_coordinator.generate_historical_report(start_date, end_date)
            self.logger.info("Generated historical report for %s to %s", start_date, end_date)
        except DATA_ACCESS_ERRORS as exc:  # policy_guard: allow-silent-handler
            self.logger.error(
                "Error generating historical report (%s): %s",
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            return "❌ Error generating historical report"
        else:
            return result

    async def generate_current_day_report(self) -> str:
        try:
            result = await self.report_coordinator.generate_current_day_report()
            self.logger.info("Generated current day report")
        except DATA_ACCESS_ERRORS as exc:  # policy_guard: allow-silent-handler
            self.logger.error(
                "Error generating current day report (%s): %s",
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            return "❌ Error generating current day report"
        else:
            return result

    async def generate_settlement_notification(self, trade_date: date, settled_markets: list, daily_report: str) -> str:
        return await self.summary_builder.generate_settlement_notification(trade_date, settled_markets, daily_report)

    async def generate_summary_stats(self, days_back: int = 30) -> str:
        try:
            return await self.summary_builder.generate_summary_stats(days_back)
        except DATA_ACCESS_ERRORS as exc:  # policy_guard: allow-silent-handler
            self.logger.error("Error generating summary stats (%s): %s", type(exc).__name__, exc, exc_info=True)
            return "❌ Error generating summary statistics"

    async def generate_unified_pnl_report(self) -> str:
        try:
            return await self.unified_builder.generate_unified_pnl_report()
        except DATA_ACCESS_ERRORS as exc:  # policy_guard: allow-silent-handler
            self.logger.error(
                "Error generating unified P&L report (%s): %s",
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            return "❌ Error generating unified P&L report"

    async def generate_unified_pnl_data(self) -> Dict[str, Any]:
        try:
            return await self.unified_builder.generate_unified_pnl_data()
        except DATA_ACCESS_ERRORS as exc:
            self.logger.error("Error generating unified P&L data (%s): %s", type(exc).__name__, exc, exc_info=True)
            raise
