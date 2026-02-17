"""
Redis connection lifecycle management for subscription store.
"""

import logging
from typing import Optional

from redis.asyncio import Redis

from ..typing import RedisClient, ensure_awaitable

logger = logging.getLogger(__name__)


class SubscriptionStoreConnectionManager:
    """Manages Redis connection lifecycle for subscription operations"""

    def __init__(self, pool=None):
        """Initialize with optional connection pool

        Args:
            pool: Optional Redis connection pool
        """
        self.pool = pool
        self.redis: Optional[RedisClient] = None
        self.pubsub = None
        self._initialized = False
        self._parent_store = None

    @property
    def initialized(self) -> bool:
        return self._initialized

    @initialized.setter
    def initialized(self, value: bool) -> None:
        self._initialized = value

    def set_parent(self, parent_store):
        """Set parent store reference.

        Args:
            parent_store: Parent SubscriptionStore instance
        """
        self._parent_store = parent_store

    async def get_redis(self) -> RedisClient:
        """Get Redis connection, reconnecting if the connection has dropped.

        Returns:
            Active Redis client

        Raises:
            RuntimeError: If connection not initialized
            ConnectionError: If ping or reconnection fails
        """
        if not self._initialized or self.redis is None:
            raise RuntimeError("Redis connection not initialized. Use 'async with SubscriptionStore()' context manager.")
        try:
            await self._ping_check()
        except (ConnectionError, OSError, TimeoutError) as exc:
            logger.warning("Redis connection lost, attempting reconnect")
            await self._reconnect()
            raise ConnectionError("Redis connection was lost and re-established") from exc
        return self.redis

    async def _ping_check(self) -> None:
        """Verify the Redis connection is alive by issuing a ping."""
        ping = getattr(self.redis, "ping", None)
        if ping is None:
            return
        await ensure_awaitable(ping())

    async def _reconnect(self) -> None:
        """Re-establish the Redis connection from the existing pool."""
        await self.cleanup()
        await self.initialize()

    async def initialize(self):
        """Setup Redis connection from pool"""
        if not self.pool:
            from .. import connection

            self.pool = await connection.get_redis_pool()

        self.redis = Redis(connection_pool=self.pool, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        self._initialized = True

    async def cleanup(self):
        """Cleanup resources"""
        if self.pubsub:
            await ensure_awaitable(self.pubsub.aclose())
            self.pubsub = None
        if self.redis:
            await ensure_awaitable(self.redis.aclose())
        self.redis = None
        self._initialized = False
