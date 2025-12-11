"""
Close date operations for PnL reporting.

Handles report generation for trades closed today and yesterday.
"""

import logging
from typing import List, Tuple

from ..data_models.trade_record import PnLReport, TradeRecord
from ..redis_protocol.trade_store import TradeStore
from .base_operations import BaseReportOperations
from .data_access_errors import DATA_ACCESS_ERRORS
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class CloseDateOperations(BaseReportOperations):
    """Manages close date operations for PnL reporting."""

    def __init__(self, trade_store: TradeStore, report_generator: ReportGenerator):
        super().__init__(trade_store, report_generator, logger)

    async def generate_today_close_date_report(self) -> PnLReport:
        """
        Generate P&L report for trades that closed today.

        Returns:
            P&L report for today's closed trades
        """
        try:
            trades = await self.trade_store.get_trades_closed_today()
            return await self.report_generator.generate_aggregated_report_by_close_date(trades)
        except DATA_ACCESS_ERRORS as exc:
            self.logger.exception("Error generating today close-date report (%s)", type(exc).__name__)
            raise

    async def generate_yesterday_close_date_report(self) -> PnLReport:
        """
        Generate P&L report for trades that closed yesterday.

        Returns:
            P&L report for yesterday's closed trades
        """
        try:
            trades = await self.trade_store.get_trades_closed_yesterday()
            return await self.report_generator.generate_aggregated_report_by_close_date(trades)
        except DATA_ACCESS_ERRORS as exc:
            self.logger.exception("Error generating yesterday close-date report (%s)", type(exc).__name__)
            raise

    async def get_today_close_date_trades_and_report(
        self,
    ) -> Tuple[List[TradeRecord], PnLReport]:
        """
        Get both trades and P&L report for trades that closed today.

        Returns:
            Tuple of (trades, report) for accurate contract calculation
        """
        try:
            trades = await self.trade_store.get_trades_closed_today()
            report = await self.report_generator.generate_aggregated_report_by_close_date(trades)
        except DATA_ACCESS_ERRORS as exc:
            self.logger.exception(
                "Error getting today close-date trades and report (%s)",
                type(exc).__name__,
            )
            raise
        else:
            return trades, report

    async def get_yesterday_close_date_trades_and_report(
        self,
    ) -> Tuple[List[TradeRecord], PnLReport]:
        """
        Get both trades and P&L report for trades that closed yesterday.

        Returns:
            Tuple of (trades, report) for accurate contract calculation
        """
        try:
            trades = await self.trade_store.get_trades_closed_yesterday()
            report = await self.report_generator.generate_aggregated_report_by_close_date(trades)
        except DATA_ACCESS_ERRORS as exc:
            self.logger.exception(
                "Error getting yesterday close-date trades and report (%s)",
                type(exc).__name__,
            )
            raise
        else:
            return trades, report
