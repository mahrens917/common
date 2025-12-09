"""Connection management for Redis persistence operations."""

import asyncio
import logging
from typing import Optional

from redis.asyncio import Redis

from .. import get_redis_pool
from ..error_types import REDIS_ERRORS
from ..typing import RedisClient, ensure_awaitable

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages Redis connection lifecycle for persistence operations."""

    def __init__(self):
        """Initialize connection manager."""
        self.redis: Optional[RedisClient] = None
        self._pool = None
        self._initialized = False

    async def get_redis(self) -> RedisClient:
        """
        Get Redis connection, ensuring it's properly initialized.

        Returns:
            Redis: Active Redis connection

        Raises:
            RuntimeError: If Redis connection cannot be established
        """
        if self.redis is None or not self._initialized:
            if not await self.ensure_connection():
                raise RuntimeError("Failed to establish Redis connection")

        # Test connection health
        try:
            redis = self.redis
            if redis is None:
                raise RuntimeError("Redis connection unexpectedly unavailable")
            await asyncio.wait_for(ensure_awaitable(redis.ping()), timeout=5.0)
        except (asyncio.TimeoutError, *REDIS_ERRORS) as exc:
            if not await self.ensure_connection():
                raise RuntimeError(f"Failed to re-establish Redis connection") from exc

        redis = self.redis
        assert redis is not None, "Redis connection should be established"
        return redis

    async def ensure_connection(self) -> bool:
        """
        Ensure that Redis connection is established.

        Returns:
            bool: True if connection is established, False otherwise
        """
        try:
            self._pool = await get_redis_pool()
            self.redis = Redis(connection_pool=self._pool, decode_responses=True)

            # Test connection
            redis = self.redis
            assert redis is not None
            await ensure_awaitable(redis.ping())
            self._initialized = True
            logger.debug("RedisPersistenceManager Redis connection established")

        except REDIS_ERRORS as exc:
            logger.error("Failed to establish Redis connection: %s", exc, exc_info=True)
            return False
        else:
            return True

    async def close(self) -> None:
        """Close the Redis connection and cleanup resources."""
        if self.redis:
            redis = self.redis
            try:
                await redis.aclose()
            except REDIS_ERRORS:
                logger.debug("Failed to close Redis client cleanly", exc_info=True)
            finally:
                self.redis = None
                self._pool = None
                self._initialized = False

    def set_redis(self, redis: Optional[RedisClient]) -> None:
        """
        Set an existing Redis connection.

        Args:
            redis: Redis connection to use
        """
        self.redis = redis
        self._initialized = redis is not None
