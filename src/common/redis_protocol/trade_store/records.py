from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

from redis import WatchError

from ...data_models.trade_record import TradeRecord
from ..typing import RedisClient, ensure_awaitable
from .codec import TradeRecordCodec
from .errors import TradeStoreError
from .keys import TradeKeyBuilder
from .traderecordrepository_helpers.data_access import RepositoryDataAccess

_WATCH_MAX_RETRIES = 10
_WATCH_BASE_DELAY = 0.01


class TradeRecordRepository:
    def __init__(
        self,
        redis_provider: Callable[[], Awaitable[RedisClient]],
        *,
        key_builder: TradeKeyBuilder,
        codec: TradeRecordCodec,
        logger,
    ) -> None:
        self._redis_provider = redis_provider
        self._keys = key_builder
        self._codec = codec
        self._logger = logger
        self._data = RepositoryDataAccess(lambda: self._redis_provider(), key_builder=key_builder, codec=codec)

    async def store(self, trade: TradeRecord) -> bool:
        client = await self._redis_provider()
        trade_json = self._codec.encode(trade)
        async with client.pipeline() as pipe:
            trade_date = trade.trade_timestamp.date()
            trade_key = self._keys.trade(trade_date, trade.order_id)
            pipe.set(trade_key, trade_json)
            pipe.sadd(self._keys.date_index(trade_date), trade.order_id)
            if trade.weather_station:
                pipe.sadd(self._keys.station(trade.weather_station), trade.order_id)
            pipe.sadd(self._keys.category(trade.market_category), trade.order_id)
            pipe.sadd(self._keys.rule(trade.trade_rule), trade.order_id)
            pipe.set(self._keys.order_index(trade.order_id), trade_key)
            results = await ensure_awaitable(pipe.execute())
        failed_ops = [idx for idx, result in enumerate(results) if result is None or result is False]
        if failed_ops:
            raise TradeStoreError(f"Redis pipeline operations failed at indices: {failed_ops}")
        self._logger.debug("Stored trade %s for %s", trade.order_id, trade_date)
        return True

    async def get(self, trade_date, order_id: str) -> Optional[TradeRecord]:
        client = await self._redis_provider()
        trade_key = self._keys.trade(trade_date, order_id)
        trade_json = await ensure_awaitable(client.get(trade_key))
        if not trade_json:
            return None
        return self._codec.decode(trade_json)

    async def get_by_order_id(self, order_id: str) -> Optional[TradeRecord]:
        client = await self._redis_provider()
        trade_key = await ensure_awaitable(client.get(self._keys.order_index(order_id)))
        if trade_key is None:
            return None
        trade_json = await ensure_awaitable(client.get(trade_key))
        if not trade_json:
            raise TradeStoreError(f"Indexed trade payload missing for order {order_id}: {trade_key!r}")
        return self._codec.decode(trade_json)

    async def mark_settled(
        self,
        order_id: str,
        *,
        settlement_price_cents: int,
        settled_at: Optional[datetime],
        timestamp_provider: Callable[[], datetime],
    ) -> bool:
        client = await self._redis_provider()
        order_index_key = self._keys.order_index(order_id)
        for watch_attempt in range(_WATCH_MAX_RETRIES):
            try:
                trade_key = await ensure_awaitable(client.get(order_index_key))
                if not trade_key:
                    raise TradeStoreError(f"Order id {order_id} not indexed; cannot mark settled")
                async with client.pipeline() as pipe:
                    await ensure_awaitable(pipe.watch(order_index_key, trade_key))
                    trade_json = await ensure_awaitable(pipe.get(trade_key))
                    if not trade_json:
                        await ensure_awaitable(pipe.unwatch())
                        raise TradeStoreError(f"Trade key {trade_key} missing for order {order_id}")
                    trade_record = self._codec.decode(trade_json)
                    trade_record.settlement_price_cents = settlement_price_cents
                    trade_record.settlement_time = settled_at or timestamp_provider()
                    updated_payload = self._codec.encode(trade_record)
                    pipe.multi()
                    pipe.set(trade_key, updated_payload)
                    await ensure_awaitable(pipe.execute())
                break
            except WatchError as exc:
                if watch_attempt >= _WATCH_MAX_RETRIES - 1:
                    raise TradeStoreError(f"Optimistic lock failed after {_WATCH_MAX_RETRIES} retries for order {order_id}") from exc
                await asyncio.sleep(_WATCH_BASE_DELAY * (2**watch_attempt))
        self._logger.info("Marked trade %s as settled at %s", order_id, settlement_price_cents)
        return True

    async def redis_client(self) -> RedisClient:
        return await self._data.redis_client()

    def build_trade_key(self, trade_date, order_id: str) -> str:
        return self._data.build_trade_key(trade_date, order_id)

    def decode_trade(self, trade_json: Any) -> TradeRecord:
        return self._data.decode_trade(trade_json)

    def encode_trade(self, trade: TradeRecord) -> Any:
        return self._data.encode_trade(trade)

    async def save_without_reindex(self, trade: TradeRecord) -> None:
        await self._data.save_without_reindex(trade)

    async def load_all_for_date(self, trade_date) -> List[str]:
        return await self._data.load_all_for_date(trade_date)

    async def load_index(self, key: str) -> List[str]:
        return await self._data.load_index(key)

    async def load_trade_payload(self, trade_key: str) -> Dict[str, Any]:
        return await self._data.load_trade_payload(trade_key)


__all__ = ["TradeRecordRepository"]
