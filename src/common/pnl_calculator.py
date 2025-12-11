"""
Profit and Loss calculator for Kalshi trading report system.

This module calculates P&L for individual trades and generates aggregated
reports with breakdowns by weather station, time, and trading rules.
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Tuple

from .data_models.trade_record import PnLReport, TradeRecord
from .pnl_calculator_helpers.dependencies_factory import (
    PnLCalculatorDependencies,
    PnLCalculatorDependenciesFactory,
)
from .redis_protocol.trade_store import TradeStore
from .time_utils import load_configured_timezone

logger = logging.getLogger(__name__)


class PnLCalculator:
    """Calculates profit/loss for trades and generates comprehensive reports."""

    def __init__(
        self,
        trade_store: TradeStore,
        *,
        dependencies: Optional[PnLCalculatorDependencies] = None,
    ):
        self.trade_store = trade_store
        self.logger = logger
        self.timezone = load_configured_timezone()
        deps = dependencies or PnLCalculatorDependenciesFactory.create(trade_store)
        self.pnl_engine = deps.pnl_engine
        self.report_generator = deps.report_generator
        self.snapshot_manager = deps.snapshot_manager
        self.daily_ops = deps.daily_ops
        self.close_date_ops = deps.close_date_ops
        self.date_range_ops = deps.date_range_ops
        self.summary_calc = deps.summary_calc
        self.unified_calc = deps.unified_calc
        self.update_mgr = deps.update_mgr

    async def calculate_unrealized_pnl(self, trades: List[TradeRecord]) -> int:
        return await self.pnl_engine.calculate_unrealized_pnl(trades)

    async def generate_aggregated_report(self, start_date: date, end_date: date) -> PnLReport:
        return await self.report_generator.generate_aggregated_report(start_date, end_date)

    async def generate_aggregated_report_by_close_date(self, trades: List[TradeRecord]) -> PnLReport:
        return await self.report_generator.generate_aggregated_report_by_close_date(trades)

    async def calculate_daily_summary(self, trade_date: date) -> Optional[Dict]:
        return await self.summary_calc.calculate_daily_summary(trade_date)

    async def get_current_day_unrealized_pnl(self) -> int:
        return await self.daily_ops.get_current_day_unrealized_pnl()

    async def get_yesterday_unrealized_pnl(self) -> int:
        return await self.daily_ops.get_yesterday_unrealized_pnl()

    async def generate_today_close_date_report(self) -> PnLReport:
        return await self.close_date_ops.generate_today_close_date_report()

    async def generate_yesterday_close_date_report(self) -> PnLReport:
        return await self.close_date_ops.generate_yesterday_close_date_report()

    async def get_today_close_date_trades_and_report(
        self,
    ) -> Tuple[List[TradeRecord], PnLReport]:
        return await self.close_date_ops.get_today_close_date_trades_and_report()

    async def get_yesterday_close_date_trades_and_report(
        self,
    ) -> Tuple[List[TradeRecord], PnLReport]:
        return await self.close_date_ops.get_yesterday_close_date_trades_and_report()

    async def get_date_range_trades_and_report(self, start_date: date, end_date: date) -> Tuple[List[TradeRecord], PnLReport]:
        return await self.date_range_ops.get_date_range_trades_and_report(start_date, end_date)

    async def store_unrealized_pnl_snapshot(self, date_key: date, unrealized_pnl_cents: int) -> None:
        await self.snapshot_manager.store_unrealized_pnl_snapshot(date_key, unrealized_pnl_cents)

    async def get_unrealized_pnl_snapshot(self, date_key: date) -> Optional[int]:
        return await self.snapshot_manager.get_unrealized_pnl_snapshot(date_key)

    async def get_unified_pnl_for_date(self, target_date: date) -> int:
        return await self.unified_calc.get_unified_pnl_for_date(target_date)

    async def get_today_unified_pnl(self) -> int:
        return await self.unified_calc.get_today_unified_pnl()

    async def get_yesterday_unified_pnl(self) -> int:
        return await self.unified_calc.get_yesterday_unified_pnl()

    async def update_daily_unrealized_pnl(self, target_date: date) -> int:
        return await self.update_mgr.update_daily_unrealized_pnl(target_date)
