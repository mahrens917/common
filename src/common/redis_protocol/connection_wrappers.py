"""Async Redis connection wrapper utilities."""

from __future__ import annotations

from typing import Optional

import redis.asyncio

from .connection_pool_core import (
    REDIS_SETUP_ERRORS,
    get_redis_client,
    logger,
    record_pool_acquired,
    record_pool_returned,
)


class RedisConnection:
    """
    Redis connection wrapper using unified pool.

    Why: Provides interface expected by test mocks
    How: Wraps Redis connection with expected methods using unified pool
    """

    def __init__(self):
        """Initialize Redis connection."""
        self._client: Optional[redis.asyncio.Redis] = None

    async def connect(self) -> redis.asyncio.Redis:
        """
        Connect to Redis using unified pool.

        Delegates to canonical get_redis_client() implementation.

        Returns:
            Redis client instance

        Raises:
            ConnectionError: If Redis connection fails
        """
        if not self._client:
            try:
                self._client = await get_redis_client()
                await self._client.ping()
                record_pool_acquired()
                logger.info("RedisConnection established connection using unified pool")
            except REDIS_SETUP_ERRORS as exc:  # policy_guard: allow-silent-handler
                logger.exception(
                    "Failed to establish Redis connection (%s)",
                    type(exc).__name__,
                )
                raise ConnectionError(f"Redis connection failed") from exc

        assert self._client is not None, "Redis client should be initialized after connect()"
        return self._client

    async def get_client(self) -> redis.asyncio.Redis:
        """
        Get Redis client.

        Returns:
            Redis client instance
        """
        if not self._client:
            await self.connect()
        # After connect(), self._client is guaranteed to be non-None or an exception was raised
        assert self._client is not None, "Redis client should be initialized after connect()"
        return self._client

    async def close(self):
        """Close Redis connection and track return to pool."""
        if self._client:
            try:
                await self._client.aclose()
                record_pool_returned()  # Track connection return
                logger.info("RedisConnection closed connection")
            except REDIS_SETUP_ERRORS as exc:  # policy_guard: allow-silent-handler
                logger.warning(
                    "Error closing Redis connection (%s): %s",
                    type(exc).__name__,
                    exc,
                )
            finally:
                self._client = None


class RedisConnectionManager:
    """
    Redis connection manager using unified pool.

    Why: Provides centralized connection management for testing
    How: Manages async Redis connections with proper cleanup using unified pool
    """

    def __init__(self):
        """Initialize Redis connection manager."""
        self._connection: Optional[redis.asyncio.Redis] = None

    async def get_connection(self) -> redis.asyncio.Redis:
        """
        Get Redis connection using unified pool.

        Delegates to canonical get_redis_client() implementation.

        Returns:
            Redis connection instance

        Raises:
            ConnectionError: If Redis connection fails
        """
        if not self._connection:
            try:
                self._connection = await get_redis_client()
                record_pool_acquired()
                logger.info("Redis connection manager established connection using unified pool")
            except REDIS_SETUP_ERRORS as exc:  # policy_guard: allow-silent-handler
                logger.exception(
                    "Failed to establish Redis connection (%s)",
                    type(exc).__name__,
                )
                raise ConnectionError(f"Redis connection failed") from exc

        assert self._connection is not None, "Redis connection should be initialized after get_connection()"
        return self._connection

    async def close(self):
        """
        Close Redis connection and track return to pool.

        Why: Prevents connection leaks in test suite
        How: Properly closes connection and resets state
        """
        if self._connection:
            try:
                await self._connection.aclose()
                record_pool_returned()
                logger.info("Redis connection manager closed connection")
            except REDIS_SETUP_ERRORS as exc:  # policy_guard: allow-silent-handler
                logger.warning(
                    "Error closing Redis connection (%s): %s",
                    type(exc).__name__,
                    exc,
                )
            finally:
                self._connection = None
