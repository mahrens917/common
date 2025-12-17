"""
Kalshi market status collection.

Fetches exchange and trading status from Kalshi API and caches in Redis.
"""

import asyncio
from typing import Any, Dict, Optional

from redis.asyncio import Redis

from common.kalshi_api.client import KalshiClient
from common.kalshi_client_mixin import KalshiClientMixin


class KalshiMarketStatusCollector(KalshiClientMixin):
    """Collects Kalshi exchange status via API."""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client
        self._kalshi_client: Optional[KalshiClient] = None
        self._kalshi_client_lock = asyncio.Lock()

    async def get_kalshi_market_status(self) -> Dict[str, Any]:
        """Fetch Kalshi exchange and trading status directly from the Kalshi API."""
        kalshi_client = await self._get_kalshi_client()
        status = await kalshi_client.get_exchange_status()

        redis_client = self.redis_client
        assert redis_client is not None, "Redis client required for status caching"
        pipeline = redis_client.pipeline()
        if status["exchange_active"]:
            exchange_active_value = "true"
        else:
            exchange_active_value = "false"
        pipeline.set("kalshi:exchange_active", exchange_active_value)

        if status["trading_active"]:
            trading_active_value = "true"
        else:
            trading_active_value = "false"
        pipeline.set("kalshi:trading_active", trading_active_value)
        await pipeline.execute()

        return status
