"""Redis client management for StatusReporterMixin."""

from typing import Optional

from redis.asyncio import Redis


async def get_redis_client_for_reporter(
    redis_client: Optional[Redis], redis_client_cached: Optional[Redis]
) -> Redis:
    """
    Get Redis client, creating one if necessary.

    Args:
        redis_client: Injected Redis client (if provided)
        redis_client_cached: Lazily created Redis client (if already created)

    Returns:
        Redis client instance
    """
    from common.redis_utils import get_redis_connection

    if redis_client is not None:
        return redis_client

    if redis_client_cached is not None:
        return redis_client_cached

    # Lazy initialization: create redis connection
    return await get_redis_connection()


__all__ = ["get_redis_client_for_reporter"]
