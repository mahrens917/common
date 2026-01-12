"""Tests for retry_config module."""

from common.redis_protocol.connection_pool_helpers.retry_config import (
    RETRY_ON_CONNECTION_ERROR,
    create_async_retry,
    create_sync_retry,
)


def test_retry_on_connection_error_contains_redis_exceptions():
    """Verify RETRY_ON_CONNECTION_ERROR contains expected Redis exception types."""
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import TimeoutError as RedisTimeoutError

    assert RedisConnectionError in RETRY_ON_CONNECTION_ERROR
    assert RedisTimeoutError in RETRY_ON_CONNECTION_ERROR


def test_create_async_retry_returns_retry_object():
    """Verify create_async_retry returns a Retry object with correct config."""
    from redis.asyncio.retry import Retry

    retry = create_async_retry()

    assert isinstance(retry, Retry)


def test_create_sync_retry_returns_retry_object():
    """Verify create_sync_retry returns a Retry object with correct config."""
    from redis.retry import Retry

    retry = create_sync_retry()

    assert isinstance(retry, Retry)
