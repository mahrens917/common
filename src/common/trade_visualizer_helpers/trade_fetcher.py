from __future__ import annotations

"""Trade fetcher for visualization."""

import asyncio
import logging
from datetime import datetime
from typing import Iterable, List

from common.config.redis_schema import TradeKeys
from common.data_models.trade_record import TradeRecord
from common.redis_protocol.trade_store import TradeStore
from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.redis_utils import get_redis_connection
from common.time_helpers.timezone import ensure_timezone_aware

logger = logging.getLogger(__name__)


class TradeFetcher:
    """Fetch executed trades from Redis."""

    def __init__(self, trade_store: TradeStore) -> None:
        self._trade_store = trade_store

    async def get_executed_trades_for_station(
        self,
        station_icao: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[TradeRecord]:
        """Fetch executed trades for a station within time range."""
        redis: RedisClient | None = None
        try:
            redis = await get_redis_connection()
            station_key = TradeKeys.by_station(station_icao)
            order_ids = list(await ensure_awaitable(redis.smembers(station_key)))

            start_aware, end_aware = self._normalize_range(start_time, end_time)
            trades = await self._collect_trades(order_ids, start_aware, end_aware)
        except asyncio.CancelledError:
            raise
        except (
            OSError,
            ConnectionError,
            RuntimeError,
            ValueError,
            Exception,
        ):  # pragma: no cover - defensive logging
            logger.exception("Failed to fetch executed trades for %s", station_icao)
            return []
        else:
            return trades
        finally:
            if redis:
                await redis.aclose()

    @staticmethod
    def _normalize_range(start_time: datetime, end_time: datetime) -> tuple[datetime, datetime]:
        """Ensure both timestamps are timezone aware using UTC when missing tzinfo."""
        return (
            TradeFetcher._ensure_aware(start_time),
            TradeFetcher._ensure_aware(end_time),
        )

    @staticmethod
    def _ensure_aware(timestamp: datetime) -> datetime:
        """Return a timezone-aware datetime in UTC (delegates to canonical)."""
        return ensure_timezone_aware(timestamp)

    async def _collect_trades(self, order_ids: Iterable[str | bytes], start_aware: datetime, end_aware: datetime) -> List[TradeRecord]:
        """Fetch trades for provided ids that fall within the requested range."""
        trades: List[TradeRecord] = []
        for raw_order_id in order_ids:
            order_id = raw_order_id.decode("utf-8") if isinstance(raw_order_id, bytes) else raw_order_id
            trade = await self._trade_store.get_trade_by_order_id(order_id)
            if not trade:
                continue

            trade_time = self._ensure_aware(trade.trade_timestamp)
            if start_aware <= trade_time <= end_aware:
                trades.append(trade)
        return trades
