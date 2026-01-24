"""
Pool management for RedisConnectionManager
"""

import logging
from typing import Any, Optional

from redis.asyncio import Redis

from ... import cleanup_redis_pool
from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable

logger = logging.getLogger(__name__)


class PoolManager:
    """Manages Redis connection pool creation and cleanup"""

    def __init__(self):
        """Initialize pool manager"""
        pass

    @staticmethod
    async def create_redis_client() -> Redis:
        """
        Create a new Redis client with connection pool.

        Delegates to canonical get_redis_client() from connection_pool_core
        to ensure consistent connection pooling across the codebase.
        """
        from common.redis_protocol.connection_pool_core import get_redis_client

        return await get_redis_client()

    @staticmethod
    async def close_redis_client(redis_client: Any) -> None:
        """Close Redis client connection"""
        aclose_fn = getattr(redis_client, "aclose", None)
        if callable(aclose_fn):
            try:
                await ensure_awaitable(aclose_fn())
            except REDIS_ERRORS:  # Expected exception in operation  # policy_guard: allow-silent-handler
                logger.debug("Failed to close Redis client cleanly", exc_info=True)

    @staticmethod
    async def cleanup_pool() -> None:
        """Cleanup Redis connection pool"""
        try:
            import importlib

            kalshi_store_pkg = importlib.import_module("common.redis_protocol.kalshi_store")
            cleanup = getattr(kalshi_store_pkg, "cleanup_redis_pool", cleanup_redis_pool)
            await cleanup()
        except RuntimeError:  # Expected runtime failure in operation  # policy_guard: allow-silent-handler
            logger.debug(
                "Event loop already closed when cleaning up pool; skipping pool cleanup",
                exc_info=True,
            )
        except REDIS_ERRORS:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.debug("Error cleaning up Redis pool", exc_info=True)

    async def acquire_pool(self, *, allow_reuse: bool, redis: Optional[Redis], close_callback) -> Redis:
        """Acquire a Redis connection pool"""
        if allow_reuse and redis is not None:
            logger.debug("Reusing existing Redis connection")
            return redis

        if redis is not None:
            await close_callback(redis)

        logger.debug("Creating new Redis connection (allow_reuse=%s)", allow_reuse)
        return await self.create_redis_client()
