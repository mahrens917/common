"""
Redis initialization and connection management for OptimizedMarketStore
"""

import logging
from typing import Any, Optional

import redis.asyncio
from redis.asyncio import ConnectionPool, Redis

from ..atomic_operations import AtomicRedisOperations
from ..connection import get_redis_pool
from ..error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class RedisInitializer:
    """Handles Redis connection initialization for OptimizedMarketStore"""

    @staticmethod
    def _is_redis_like(candidate: Any) -> bool:
        required_attrs = ("hgetall", "hset", "pipeline", "publish")
        return all(hasattr(candidate, attr) for attr in required_attrs)

    @staticmethod
    def initialize_from_pool_or_client(
        redis_or_pool: Any,
    ) -> tuple[Any, Optional[ConnectionPool], bool, Optional[AtomicRedisOperations]]:
        """
        Initialize Redis connection from pool or client

        Args:
            redis_or_pool: Async Redis connection or async ConnectionPool

        Returns:
            Tuple of (redis_client, redis_pool, initialized, atomic_ops)

        Raises:
            ValueError: If redis_or_pool is not a valid Redis connection or pool
        """
        redis_client: Optional[Any] = None
        redis_pool: Optional[ConnectionPool] = None
        initialized = False

        if isinstance(redis_or_pool, ConnectionPool):
            redis_pool = redis_or_pool
            redis_client = redis.asyncio.Redis(connection_pool=redis_pool, decode_responses=True)
            initialized = True
        elif isinstance(redis_or_pool, Redis):
            redis_client = redis_or_pool
            if hasattr(redis_client, "connection_pool"):
                redis_pool = redis_client.connection_pool
            initialized = True
        elif RedisInitializer._is_redis_like(redis_or_pool):
            redis_client = redis_or_pool
            if hasattr(redis_or_pool, "connection_pool"):
                redis_pool = redis_or_pool.connection_pool
            initialized = True
        else:
            raise TypeError(f"redis_or_pool must be an async Redis connection or async ConnectionPool, got {type(redis_or_pool)}")

        atomic_ops = AtomicRedisOperations(redis_client) if redis_client else None

        return redis_client, redis_pool, initialized, atomic_ops

    @staticmethod
    async def create_with_pool() -> tuple[Any, Optional[ConnectionPool], bool, Optional[AtomicRedisOperations]]:
        """
        Create a new Redis connection with a connection pool

        Returns:
            Tuple of (redis_client, redis_pool, initialized, atomic_ops)

        Raises:
            Exception: If Redis pool creation fails
        """
        try:
            pool = await get_redis_pool()
            return RedisInitializer.initialize_from_pool_or_client(pool)
        except REDIS_ERRORS as exc:
            logger.error("Error creating Redis connection with pool: %s", exc, exc_info=True)
            raise
