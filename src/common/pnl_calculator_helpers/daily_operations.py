"""
Daily PnL operations for current and previous day.

Handles unrealized PnL calculations for today and yesterday.
"""

import asyncio
import logging
from datetime import timedelta

from redis.exceptions import RedisError

from ..redis_protocol.trade_store import TradeStore, TradeStoreError
from ..redis_utils import RedisOperationError
from ..time_utils import get_timezone_aware_date, load_configured_timezone
from .pnl_calculator import PnLCalculationEngine

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


class DailyOperations:
    """Manages daily PnL operations for current and previous day."""

    def __init__(self, trade_store: TradeStore, pnl_engine: PnLCalculationEngine):
        self.trade_store = trade_store
        self.pnl_engine = pnl_engine
        self.timezone = load_configured_timezone()
        self.logger = logger

    async def get_current_day_unrealized_pnl(self) -> int:
        """
        Get unrealized P&L for current day's trades.

        Returns:
            Unrealized P&L in cents
        """
        try:
            today = get_timezone_aware_date(self.timezone)
            trades = await self.trade_store.get_trades_by_date_range(today, today)
            return await self.pnl_engine.calculate_unrealized_pnl(trades)
        except DATA_ACCESS_ERRORS as exc:  # policy_guard: allow-silent-handler
            self.logger.exception("Error calculating current day unrealized P&L (%s)", type(exc).__name__)
            return 0

    async def get_yesterday_unrealized_pnl(self) -> int:
        """
        Get unrealized P&L for yesterday's trades.

        Returns:
            Unrealized P&L in cents for trades executed yesterday that haven't settled
        """
        try:
            yesterday = get_timezone_aware_date(self.timezone) - timedelta(days=1)
            unrealized_trades = await self.trade_store.get_unrealized_trades_for_date(yesterday)
            return await self.pnl_engine.calculate_unrealized_pnl(unrealized_trades)
        except DATA_ACCESS_ERRORS as exc:  # policy_guard: allow-silent-handler
            self.logger.exception("Error calculating yesterday unrealized P&L (%s)", type(exc).__name__)
            return 0
