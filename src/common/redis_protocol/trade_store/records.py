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


def normalize_order_ids(raw_ids: Any) -> List[str]:
    """Normalize raw Redis order IDs to consistent string format."""
    order_ids: List[str] = []
    for order_id in raw_ids:
        if isinstance(order_id, bytes):
            order_ids.append(order_id.decode("utf-8"))
        else:
            order_ids.append(str(order_id))
    return order_ids


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
        return await self._redis_provider()

    def build_trade_key(self, trade_date, order_id: str) -> str:
        return self._keys.trade(trade_date, order_id)

    def decode_trade(self, trade_json: Any) -> TradeRecord:
        return self._codec.decode(trade_json)

    def encode_trade(self, trade: TradeRecord) -> Any:
        return self._codec.encode(trade)

    async def save_without_reindex(self, trade: TradeRecord) -> None:
        client = await self._redis_provider()
        trade_key = self._keys.trade(trade.trade_timestamp.date(), trade.order_id)
        await ensure_awaitable(client.set(trade_key, self._codec.encode(trade)))

    async def load_all_for_date(self, trade_date) -> List[str]:
        client = await self._redis_provider()
        order_ids = await ensure_awaitable(client.smembers(self._keys.date_index(trade_date)))
        return normalize_order_ids(order_ids)

    async def load_index(self, key: str) -> List[str]:
        client = await self._redis_provider()
        order_ids = await ensure_awaitable(client.smembers(key))
        return normalize_order_ids(order_ids)

    async def load_trade_payload(self, trade_key: str) -> Dict[str, Any]:
        client = await self._redis_provider()
        trade_json = await ensure_awaitable(client.get(trade_key))
        if not trade_json:
            raise TradeStoreError(f"Trade payload missing for key {trade_key}")
        return self._codec.to_mapping(trade_json)


__all__ = ["TradeRecordRepository"]
