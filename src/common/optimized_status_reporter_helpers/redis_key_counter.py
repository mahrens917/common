"""
Redis key counting utilities.

Efficiently counts keys matching patterns using async iteration.
"""

import asyncio
from typing import Dict, Optional

from redis.asyncio import Redis

from src.common.config.redis_schema import get_schema_config


class RedisKeyCounter:
    """Efficiently count Redis keys by namespace."""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client

    async def count_keys_async(self, pattern: str) -> int:
        """Efficiently count keys matching pattern."""
        count = 0
        redis_client = self.redis_client
        if redis_client is None:
            raise AttributeError("'NoneType' object has no attribute 'scan_iter'")
        async for _ in redis_client.scan_iter(match=pattern, count=100):
            count += 1
        return count

    async def collect_key_counts(self) -> Dict[str, int]:
        """Collect counts for all key namespaces."""
        schema = get_schema_config()
        deribit, kalshi, cfb, weather = await asyncio.gather(
            self.count_keys_async(f"{schema.deribit_market_prefix}:*"),
            self.count_keys_async(f"{schema.kalshi_market_prefix}:*"),
            self.count_keys_async("cfb:*"),
            self.count_keys_async("weather:station:*"),
        )

        return {
            "redis_deribit_keys": deribit,
            "redis_kalshi_keys": kalshi,
            "redis_cfb_keys": cfb,
            "redis_weather_keys": weather,
        }
