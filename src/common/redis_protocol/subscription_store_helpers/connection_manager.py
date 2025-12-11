"""
Redis connection lifecycle management for subscription store.
"""

from typing import Optional

from redis.asyncio import Redis

from ..typing import RedisClient, ensure_awaitable


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
        """Set parent store for backward compatibility

        Args:
            parent_store: Parent SubscriptionStore instance
        """
        self._parent_store = parent_store

    async def get_redis(self) -> RedisClient:
        """Get Redis connection, ensuring it's properly initialized

        Returns:
            Active Redis client

        Raises:
            RuntimeError: If connection not initialized
        """
        if not self._initialized or self.redis is None:
            raise RuntimeError("Redis connection not initialized. Use 'async with SubscriptionStore()' context manager.")
        assert self.redis is not None, "Redis connection should be established"
        return self.redis

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
        if self.redis:
            await ensure_awaitable(self.redis.aclose())
        self.redis = None
        self._initialized = False
