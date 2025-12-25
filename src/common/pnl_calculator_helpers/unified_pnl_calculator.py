"""
Unified PnL calculations combining realized and unrealized.

Handles calculations that combine settled and unsettled trade P&L.
"""

import asyncio
import logging
from datetime import date, timedelta

from redis.exceptions import RedisError

from ..redis_protocol.trade_store import TradeStore, TradeStoreError
from ..redis_utils import RedisOperationError
from ..time_utils import get_timezone_aware_date, load_configured_timezone

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


class UnifiedPnLCalculator:
    """Calculates unified P&L combining realized and unrealized."""

    def __init__(self, trade_store: TradeStore):
        self.trade_store = trade_store
        self.timezone = load_configured_timezone()
        self.logger = logger

    async def get_unified_pnl_for_date(self, target_date: date) -> int:
        """
        Get unified P&L for a specific date (combines realized + unrealized).

        Args:
            target_date: Date to calculate P&L for

        Returns:
            Total P&L in cents (realized + unrealized)
        """
        try:
            trades = await self.trade_store.get_trades_by_date_range(target_date, target_date)
            return sum(trade.calculate_current_pnl_cents() for trade in trades)
        except DATA_ACCESS_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            self.logger.exception(
                "Error calculating unified P&L for %s (%s)",
                target_date,
                type(exc).__name__,
            )
            return 0

    async def get_today_unified_pnl(self) -> int:
        """Get unified P&L for today."""
        today = get_timezone_aware_date(self.timezone)
        return await self.get_unified_pnl_for_date(today)

    async def get_yesterday_unified_pnl(self) -> int:
        """Get unified P&L for yesterday."""
        yesterday = get_timezone_aware_date(self.timezone) - timedelta(days=1)
        return await self.get_unified_pnl_for_date(yesterday)
