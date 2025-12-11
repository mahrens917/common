"""
Date range operations for PnL reporting.

Handles retrieval of trades and reports for arbitrary date ranges.
"""

import logging
from datetime import date
from typing import List, Tuple

from ..data_models.trade_record import PnLReport, TradeRecord
from ..redis_protocol.trade_store import TradeStore
from .base_operations import BaseReportOperations
from .data_access_errors import DATA_ACCESS_ERRORS
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class DateRangeOperations(BaseReportOperations):
    """Manages date range operations for PnL reporting."""

    def __init__(self, trade_store: TradeStore, report_generator: ReportGenerator):
        super().__init__(trade_store, report_generator, logger)

    async def get_date_range_trades_and_report(self, start_date: date, end_date: date) -> Tuple[List[TradeRecord], PnLReport]:
        """
        Get both trades and P&L report for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Tuple of (trades, report) for accurate contract calculation
        """
        try:
            trades = await self.trade_store.get_trades_by_date_range(start_date, end_date)
            report = await self.report_generator.generate_aggregated_report(start_date, end_date)
        except DATA_ACCESS_ERRORS as exc:
            self.logger.exception(
                "Error getting trades and report for %s to %s (%s)",
                start_date,
                end_date,
                type(exc).__name__,
            )
            raise
        else:
            return trades, report
