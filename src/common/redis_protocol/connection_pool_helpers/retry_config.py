"""Retry configuration for Redis connection drops."""

from __future__ import annotations

from redis.asyncio.retry import Retry as AsyncRetry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.retry import Retry as SyncRetry

from .. import config

# Exceptions that should trigger automatic retry on connection drops
# Uses Redis-specific exception types (they wrap the underlying Python exceptions)
RETRY_ON_CONNECTION_ERROR: tuple[type[RedisError], ...] = (
    RedisConnectionError,
    RedisTimeoutError,
)


def create_async_retry() -> AsyncRetry:
    """Create async retry instance with exponential backoff for connection drops."""
    backoff = ExponentialBackoff(
        cap=config.REDIS_RETRY_DELAY * (2**config.REDIS_MAX_RETRIES),
        base=config.REDIS_RETRY_DELAY,
    )
    return AsyncRetry(
        backoff=backoff,
        retries=config.REDIS_MAX_RETRIES,
        supported_errors=RETRY_ON_CONNECTION_ERROR,
    )


def create_sync_retry() -> SyncRetry:
    """Create sync retry instance with exponential backoff for connection drops."""
    backoff = ExponentialBackoff(
        cap=config.REDIS_RETRY_DELAY * (2**config.REDIS_MAX_RETRIES),
        base=config.REDIS_RETRY_DELAY,
    )
    return SyncRetry(
        backoff=backoff,
        retries=config.REDIS_MAX_RETRIES,
        supported_errors=RETRY_ON_CONNECTION_ERROR,
    )
