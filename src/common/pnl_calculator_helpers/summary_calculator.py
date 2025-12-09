"""
Daily summary calculation and caching.

Handles calculation and retrieval of daily PnL summaries.
"""

import logging
from datetime import date
from typing import Dict, Optional

from ..redis_protocol.trade_store import TradeStore
from .base_operations import BaseReportOperations
from .data_access_errors import DATA_ACCESS_ERRORS
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class SummaryCalculator(BaseReportOperations):
    """Manages daily PnL summary calculation and caching."""

    def __init__(self, trade_store: TradeStore, report_generator: ReportGenerator):
        super().__init__(trade_store, report_generator, logger)

    async def calculate_daily_summary(self, trade_date: date) -> Optional[Dict]:
        """
        Calculate daily P&L summary for quick access.

        Args:
            trade_date: Date to calculate summary for

        Returns:
            Summary dictionary or None if no trades
        """
        try:
            # Check if we have a cached summary
            cached_summary = await self.trade_store.get_daily_summary(trade_date)
            if cached_summary:
                return cached_summary

            # Generate new summary
            report = await self.report_generator.generate_aggregated_report(trade_date, trade_date)

            # Store summary for future use
            await self.trade_store.store_daily_summary(report)

            # Return simplified summary
            return {
                "date": trade_date.isoformat(),
                "total_trades": report.total_trades,
                "total_cost_cents": report.total_cost_cents,
                "total_pnl_cents": report.total_pnl_cents,
                "win_rate": report.win_rate,
            }

        except DATA_ACCESS_ERRORS as exc:
            self.logger.exception(
                "Error calculating daily summary for %s (%s)",
                trade_date,
                type(exc).__name__,
            )
            return None
