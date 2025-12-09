"""Shared mixin for components that depend on a Redis provider."""

from typing import Awaitable, Callable

from redis.asyncio import Redis


class RedisProviderMixin:
    """Stores and exposes the async Redis provider."""

    def __init__(self, redis_provider: Callable[[], Awaitable[Redis]]) -> None:
        self._redis_provider = redis_provider

    async def _get_redis(self) -> Redis:
        """Retrieve a Redis client using the configured provider."""
        return await self._redis_provider()


__all__ = ["RedisProviderMixin"]
