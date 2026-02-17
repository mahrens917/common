"""Low-level data access helpers for TradeRecordRepository."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List

from ....data_models.trade_record import TradeRecord
from ...typing import RedisClient, ensure_awaitable
from ..codec import TradeRecordCodec
from ..id_normalizer import normalize_order_ids
from ..keys import TradeKeyBuilder


class RepositoryDataAccess:
    """Encapsulates low-level Redis reads and writes for trade records."""

    def __init__(
        self,
        redis_provider: Callable[[], Awaitable[RedisClient]],
        *,
        key_builder: TradeKeyBuilder,
        codec: TradeRecordCodec,
    ) -> None:
        self._redis_provider = redis_provider
        self._keys = key_builder
        self._codec = codec

    async def redis_client(self) -> RedisClient:
        """Return the active Redis client."""
        return await self._redis_provider()

    def build_trade_key(self, trade_date, order_id: str) -> str:
        """Build the Redis key for a specific trade."""
        return self._keys.trade(trade_date, order_id)

    def decode_trade(self, trade_json: Any) -> TradeRecord:
        """Decode a serialized trade record."""
        return self._codec.decode(trade_json)

    def encode_trade(self, trade: TradeRecord) -> Any:
        """Encode a trade record for storage."""
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
            from ..errors import TradeStoreError

            raise TradeStoreError(f"Trade payload missing for key {trade_key}")
        return self._codec.to_mapping(trade_json)


__all__ = ["RepositoryDataAccess"]
