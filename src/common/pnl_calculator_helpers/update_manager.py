"""
Update manager for daily PnL snapshots.

Handles updating and storing unrealized PnL snapshots.
"""

import asyncio
import logging
from datetime import date

from redis.exceptions import RedisError

from ..redis_protocol.trade_store import TradeStore, TradeStoreError
from ..redis_utils import RedisOperationError
from .pnl_calculator import PnLCalculationEngine
from .snapshot_manager import SnapshotManager

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


class UpdateManager:
    """Manages updates to daily unrealized PnL snapshots."""

    def __init__(
        self,
        trade_store: TradeStore,
        pnl_engine: PnLCalculationEngine,
        snapshot_manager: SnapshotManager,
    ):
        self.trade_store = trade_store
        self.pnl_engine = pnl_engine
        self.snapshot_manager = snapshot_manager
        self.logger = logger

    async def update_daily_unrealized_pnl(self, target_date: date) -> int:
        """
        Calculate and store current unrealized P&L for a specific date.

        Args:
            target_date: Date to calculate unrealized P&L for

        Returns:
            Current unrealized P&L in cents
        """
        try:
            trades = await self.trade_store.get_trades_by_date_range(target_date, target_date)
            if trades:
                unrealized_pnl = await self.pnl_engine.calculate_unrealized_pnl(trades)
            else:
                unrealized_pnl = 0

            await self.snapshot_manager.store_unrealized_pnl_snapshot(target_date, unrealized_pnl)
        except DATA_ACCESS_ERRORS as exc:
            self.logger.exception(
                "Error updating daily unrealized P&L for %s (%s)",
                target_date,
                type(exc).__name__,
            )
            raise
        else:
            return unrealized_pnl
