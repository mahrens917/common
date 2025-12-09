"""
Data fetcher for Redis market data.

Handles fetching hash data from Redis with proper error handling.
"""

import logging
from typing import Dict, cast

from redis.asyncio import Redis

from ..typing import ensure_awaitable

logger = logging.getLogger(__name__)


class RedisDataValidationError(RuntimeError):
    """Raised when Redis market data cannot be validated after retries."""


class DataFetcher:
    """Fetches hash data from Redis."""

    def __init__(self, redis_client: Redis):
        """
        Initialize data fetcher.

        Args:
            redis_client: Redis connection with decode_responses=True
        """
        self.redis = redis_client
        self.logger = logger

    async def fetch_market_data(self, store_key: str) -> Dict[str, str]:
        """
        Fetch market data hash from Redis.

        Args:
            store_key: Redis key to read from

        Returns:
            Dictionary of market data fields

        Raises:
            RedisDataValidationError: If no data found for key
        """
        raw_data = cast(Dict[str, str], await ensure_awaitable(self.redis.hgetall(store_key)))
        if not raw_data:
            raise RedisDataValidationError(f"No data found for key: {store_key}")
        return raw_data
