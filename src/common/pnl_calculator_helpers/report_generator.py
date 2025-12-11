"""
PnL report generation logic.

Creates various types of P&L reports from trade data with breakdowns.
"""

import logging
from datetime import date
from typing import List

from ..data_models.trade_record import PnLReport, TradeRecord
from ..redis_protocol.trade_store import TradeStore
from ..time_utils import load_configured_timezone
from .breakdown_calculator import BreakdownCalculator
from .pnl_calculator import PnLCalculationEngine
from .reportgenerator_helpers.close_date_report_builder import CloseDateReportBuilder
from .reportgenerator_helpers.date_range_report_builder import DateRangeReportBuilder

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates comprehensive PnL reports with breakdowns."""

    def __init__(self, trade_store: TradeStore):
        self.trade_store = trade_store
        self.timezone = load_configured_timezone()
        self.pnl_engine = PnLCalculationEngine()
        self.breakdown_calculator = BreakdownCalculator()
        self.logger = logger

        # Initialize report builders
        self.date_range_builder = DateRangeReportBuilder(trade_store, self.pnl_engine, self.breakdown_calculator)
        self.close_date_builder = CloseDateReportBuilder(self.pnl_engine, self.breakdown_calculator)

    async def generate_aggregated_report(self, start_date: date, end_date: date) -> PnLReport:
        """Generate comprehensive P&L report for a date range using current market values."""
        return await self.date_range_builder.build_report(start_date, end_date)

    async def generate_aggregated_report_by_close_date(self, trades: List[TradeRecord]) -> PnLReport:
        """Generate comprehensive P&L report for trades filtered by close date."""
        return await self.close_date_builder.build_report(trades)
