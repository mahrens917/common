from __future__ import annotations

"""
Order metadata persistence helpers.

Order metadata is captured separately so fills can enrich trades without
reaching into order-processing pipelines. The store enforces validation before
persisting to Redis to ensure downstream consumers always see complete data.
"""

from typing import Any, Awaitable, Callable, Dict, Optional

from ..typing import RedisClient, ensure_awaitable
from .codec import OrderMetadataCodec
from .keys import TradeKeyBuilder


class OrderMetadataStore:
    """Persist and retrieve order metadata required for trade enrichment."""

    def __init__(
        self,
        redis_provider: Callable[[], Awaitable[RedisClient]],
        *,
        key_builder: TradeKeyBuilder,
        codec: OrderMetadataCodec,
        logger,
    ) -> None:
        self._redis_provider = redis_provider
        self._keys = key_builder
        self._codec = codec
        self._logger = logger

    async def store(
        self,
        order_id: str,
        *,
        trade_rule: str,
        trade_reason: str,
        market_category: Optional[str],
        weather_station: Optional[str],
    ) -> bool:
        client = await self._redis_provider()
        metadata = self._codec.encode(
            order_id=order_id,
            trade_rule=trade_rule,
            trade_reason=trade_reason,
            market_category=market_category,
            weather_station=weather_station,
        )
        await ensure_awaitable(client.set(self._keys.order_metadata(order_id), metadata))
        self._logger.debug("Persisted metadata for %s", order_id)
        return True

    async def load(self, order_id: str) -> Optional[Dict[str, Any]]:
        client = await self._redis_provider()
        metadata = await ensure_awaitable(client.get(self._keys.order_metadata(order_id)))
        if not metadata:
            return None
        return self._codec.decode(metadata, order_id=order_id)


__all__ = ["OrderMetadataStore"]
