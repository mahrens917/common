"""
Unrealized PnL snapshot storage and retrieval.

Manages Redis persistence of daily unrealized PnL snapshots.
"""

import asyncio
import logging
from datetime import date
from typing import Optional

from redis.exceptions import RedisError

from ..redis_protocol.trade_store import TradeStore, TradeStoreError
from ..redis_utils import RedisOperationError
from ..time_utils import get_current_utc

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


class SnapshotManager:
    """Manages unrealized PnL snapshot storage and retrieval."""

    def __init__(self, trade_store: TradeStore):
        self.trade_store = trade_store
        self.logger = logger

    async def store_unrealized_pnl_snapshot(self, date_key: date, unrealized_pnl_cents: int) -> None:
        """
        Store unrealized P&L snapshot in Redis for a specific date.

        Args:
            date_key: Date for the snapshot
            unrealized_pnl_cents: Unrealized P&L value in cents
        """
        try:
            redis_key = f"pnl:unrealized:{date_key.isoformat()}"
            await self.trade_store.store_unrealized_pnl_data(
                redis_key,
                {
                    "date": date_key.isoformat(),
                    "unrealized_pnl_cents": unrealized_pnl_cents,
                    "timestamp": get_current_utc().isoformat(),
                },
            )

            self.logger.debug(f"Stored unrealized P&L snapshot for {date_key}: {unrealized_pnl_cents} cents")

        except DATA_ACCESS_ERRORS as exc:
            self.logger.exception(
                "Error storing unrealized P&L snapshot for %s (%s)",
                date_key,
                type(exc).__name__,
            )
            raise

    async def get_unrealized_pnl_snapshot(self, date_key: date) -> Optional[int]:
        """
        Retrieve unrealized P&L snapshot from Redis for a specific date.

        Args:
            date_key: Date for the snapshot

        Returns:
            Unrealized P&L in cents, or None if not found
        """
        try:
            redis_key = f"pnl:unrealized:{date_key.isoformat()}"
            snapshot_data = await self.trade_store.get_unrealized_pnl_data(redis_key)

            if snapshot_data:
                return snapshot_data.get("unrealized_pnl_cents")

            else:
                return None
        except DATA_ACCESS_ERRORS as exc:
            self.logger.exception(
                "Error retrieving unrealized P&L snapshot for %s (%s)",
                date_key,
                type(exc).__name__,
            )
            return None
