"""
Close date report builder.

Builds PnL reports for trades filtered by close date.
"""

import asyncio
import logging
from typing import List

from redis.exceptions import RedisError

from ...data_models.trade_record import PnLReport, TradeRecord, get_trade_close_date
from ...redis_protocol.trade_store import TradeStoreError
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


class CloseDateReportBuilder:
    """Builds PnL reports for trades filtered by close date."""

    def __init__(self, pnl_engine: PnLCalculationEngine, breakdown_calculator: BreakdownCalculator):
        self.pnl_engine = pnl_engine
        self.breakdown_calculator = breakdown_calculator
        self.timezone = load_configured_timezone()
        self.empty_factory = EmptyReportFactory()
        self.logger = logger

    async def build_report(self, trades: List[TradeRecord]) -> PnLReport:
        """
        Build P&L report for trades filtered by close date.

        Args:
            trades: List of trades already filtered by close date

        Returns:
            Complete P&L report with all breakdowns
        """
        if not trades:
            today = get_timezone_aware_date(self.timezone)
            return self.empty_factory.create_empty_report(today, today)

        try:
            total_cost_cents = self.pnl_engine.calculate_total_cost(trades)
            total_pnl_cents = await self.pnl_engine.calculate_unrealized_pnl(trades)
            win_rate = self.pnl_engine.calculate_win_rate(trades)

            by_weather_station = await self.breakdown_calculator.calculate_station_breakdown(trades)
            by_rule = await self.breakdown_calculator.calculate_rule_breakdown(trades)

            close_dates = [get_trade_close_date(trade) for trade in trades]
            if close_dates:
                start_date = min(close_dates)
                end_date = max(close_dates)
            else:
                current_date = get_timezone_aware_date(self.timezone)
                start_date = current_date
                end_date = current_date

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
                "Generated close-date P&L report: %s trades, %s cents P&L",
                len(trades),
                total_pnl_cents,
            )

        except DATA_ACCESS_ERRORS:
            self.logger.exception("Error building close-date report")
            raise
        else:
            return report
