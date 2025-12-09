"""
Date range report builder.

Builds PnL reports for trades within a date range.
"""

import asyncio
import logging
from datetime import date

from redis.exceptions import RedisError

from ...data_models.trade_record import PnLReport
from ...redis_protocol.trade_store import TradeStore, TradeStoreError
from ...redis_utils import RedisOperationError
from ...time_utils import get_timezone_aware_date, load_configured_timezone
from ..breakdown_calculator import BreakdownCalculator
from ..pnl_calculator import PnLCalculationEngine
from .empty_report_factory import EmptyReportFactory

logger = logging.getLogger(__name__)

DATA_ACCESS_ERRORS = (
    TradeStoreError,
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    ValueError,
    TypeError,
)


class DateRangeReportBuilder:
    """Builds PnL reports for date ranges."""

    def __init__(
        self,
        trade_store: TradeStore,
        pnl_engine: PnLCalculationEngine,
        breakdown_calculator: BreakdownCalculator,
    ):
        self.trade_store = trade_store
        self.pnl_engine = pnl_engine
        self.breakdown_calculator = breakdown_calculator
        self.timezone = load_configured_timezone()
        self.empty_factory = EmptyReportFactory()
        self.logger = logger

    async def build_report(self, start_date: date, end_date: date) -> PnLReport:
        """
        Build P&L report for a date range using current market values.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Complete P&L report with all breakdowns
        """
        trades = await self.trade_store.get_trades_by_date_range(start_date, end_date)

        if not trades:
            return self.empty_factory.create_empty_report(start_date, end_date)

        try:
            total_cost_cents = self.pnl_engine.calculate_total_cost(trades)
            total_pnl_cents = await self.pnl_engine.calculate_unrealized_pnl(trades)
            win_rate = self.pnl_engine.calculate_win_rate(trades)

            by_weather_station = await self.breakdown_calculator.calculate_station_breakdown(trades)
            by_rule = await self.breakdown_calculator.calculate_rule_breakdown(trades)

            report = PnLReport(
                report_date=get_timezone_aware_date(self.timezone),
                start_date=start_date,
                end_date=end_date,
                total_trades=len(trades),
                total_cost_cents=total_cost_cents,
                total_pnl_cents=total_pnl_cents,
                win_rate=win_rate,
                by_weather_station=by_weather_station,
                by_rule=by_rule,
            )

            self.logger.info(
                "Generated P&L report for %s to %s: %s trades, %s cents P&L",
                start_date,
                end_date,
                len(trades),
                total_pnl_cents,
            )

        except DATA_ACCESS_ERRORS:
            self.logger.exception("Error building date-range report")
            raise
        else:
            return report
