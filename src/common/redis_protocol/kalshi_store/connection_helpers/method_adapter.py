"""
Method adapter for RedisConnectionManager
"""

from __future__ import annotations

from typing import Any, Dict

from redis.asyncio import Redis


class MethodAdapter:
    """Provides method delegation for RedisConnectionManager"""

    def __init__(self, parent: Any):
        """
        Initialize adapter

        Args:
            parent: Parent RedisConnectionManager instance
        """
        self._parent = parent

    def resolve_connection_settings(self) -> Dict[str, Any]:
        """Resolve connection settings"""
        return self._parent._property_manager.settings_resolver.resolve_connection_settings()

    async def acquire_pool(self, *, allow_reuse: bool) -> Redis:
        """Acquire Redis pool"""
        return await self._parent._pool_manager.acquire_pool(
            allow_reuse=allow_reuse,
            redis=self._parent._redis,
            close_callback=self._parent._pool_manager.close_redis_client,
        )

    async def create_redis_client(self) -> Redis:
        """Create new Redis client"""
        return await self._parent._pool_manager.create_redis_client()

    async def close_redis_client(self, redis_client: Any) -> None:
        """Close Redis client"""
        await self._parent._pool_manager.close_redis_client(redis_client)

    async def ping_connection(self, redis: Any, *, timeout: float = 5.0) -> tuple[bool, bool]:
        """Ping Redis connection"""
        return await self._parent._connection_verifier.ping_connection(redis, timeout=timeout)

    async def verify_connection(self, redis: Any) -> tuple[bool, bool]:
        """Verify Redis connection"""
        return await self._parent._connection_verifier.verify_connection(redis)

    async def connect_with_retry(self, *, allow_reuse: bool, context: str, attempts: int = 3, retry_delay: float = 0.1) -> bool:
        """Connect with retry"""
        return await self._parent._connect_with_retry(allow_reuse=allow_reuse, context=context, attempts=attempts, retry_delay=retry_delay)

    def reset_connection_state(self) -> None:
        """Reset connection state"""
        self._parent._redis = None
        self._parent._pool = None
        self._parent._initialized = False
