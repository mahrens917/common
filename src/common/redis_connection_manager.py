"""Shared Redis connection lifecycle management."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from redis.exceptions import RedisError

from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.redis_utils import RedisOperationError, get_redis_connection

logger = logging.getLogger(__name__)

REDIS_ERRORS = (
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)


class RedisConnectionManager:
    """Manages a Redis client lifecycle with event loop safety."""

    def __init__(
        self,
        connection_factory: Optional[Callable[[], Awaitable[RedisClient]]] = None,
        *,
        not_initialized_message: str = "Redis client not initialized",
    ):
        self.redis_client: Optional[RedisClient] = None
        self._connection_factory = connection_factory or get_redis_connection
        self._not_initialized_message = not_initialized_message

    async def initialize(self) -> None:
        """
        Initialize Redis connection with event loop conflict prevention.

        Always closes an existing client before creating a fresh connection to avoid
        cross-event-loop issues.
        """
        if self.redis_client is not None:
            try:
                await ensure_awaitable(self.redis_client.aclose())
            except REDIS_ERRORS:  # Expected exception in operation  # policy_guard: allow-silent-handler
                logger.warning("Error closing existing Redis connection")
            finally:
                self.redis_client = None

        try:
            self.redis_client = await self._connection_factory()
        except REDIS_ERRORS as exc:
            logger.exception("Redis connection failed: %s", type(exc).__name__)
            raise

    async def cleanup(self) -> None:
        """Clean up Redis connection to prevent resource leaks."""
        if self.redis_client is not None:
            try:
                await ensure_awaitable(self.redis_client.aclose())
            except REDIS_ERRORS:  # Expected exception in operation  # policy_guard: allow-silent-handler
                logger.warning("Error closing Redis connection during cleanup")
            finally:
                self.redis_client = None

    def get_client(self) -> RedisClient:
        """Return the active Redis client or raise if uninitialized."""
        if self.redis_client is None:
            raise ConnectionError(self._not_initialized_message)
        return self.redis_client
