from __future__ import annotations

"""
Async Redis helpers shared across Kalshi services.

This module provides a thin wrapper around the unified async connection pool
so callers avoid lingering synchronous Redis utilities.
"""


import logging
from typing import Optional, cast

import redis.asyncio

from .redis_protocol.error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class RedisOperationError(RuntimeError):
    """Raised when a Redis operation fails and should be surfaced to callers."""

    def __init__(
        self,
        operation: str,
        details: Optional[str] = None,
        original: Exception | None = None,
    ):
        message = f"Redis {operation} failed"
        if details:
            message = f"{message} ({details})"
        if original:
            message = f"{message}: {original}"
        super().__init__(message)
        self.operation = operation
        self.details = details
        self.original = original


async def get_redis_connection() -> redis.asyncio.Redis:
    """
    Obtain an async Redis client from the unified connection pool.

    Delegates to canonical implementation in common.redis_protocol.connection_pool_core.
    All connection details are sourced from the unified connection pool configuration.
    """
    from .redis_protocol.connection_pool_core import get_redis_client

    try:
        client = await get_redis_client()
    except REDIS_ERRORS as exc:
        logger.error("Redis connection failed: %s", exc, exc_info=True)
        exc_type = type(exc).__name__
        raise ConnectionError(f"Redis connection failed: {exc_type}: {exc}") from exc
    else:
        logger.debug("Redis connection established successfully")
        return client


async def ensure_keyspace_notifications(
    redis_client: redis.asyncio.Redis,
    required_flags: str = "Kh",
) -> None:
    """Enable Redis keyspace notifications for the specified event flags."""

    if not required_flags:
        return

    config_response = await redis_client.config_get("notify-keyspace-events")
    current_value = ""
    if "notify-keyspace-events" in config_response:
        current_value = config_response["notify-keyspace-events"]
    if isinstance(current_value, bytes):
        current_value = current_value.decode("utf-8")

    missing_flags = [flag for flag in required_flags if flag not in current_value]
    if not missing_flags:
        logger.debug(
            "Keyspace notifications already include required flags '%s' (current='%s')",
            required_flags,
            current_value,
        )
        return

    new_value = current_value + "".join(missing_flags)
    await redis_client.config_set("notify-keyspace-events", new_value)
    if current_value:
        rendered_current = current_value
    else:
        rendered_current = "(empty)"
    logger.info(
        "Updated Redis keyspace notifications for flags '%s' (was='%s', now='%s')",
        required_flags,
        rendered_current,
        new_value,
    )


async def cleanup_redis_connection(redis_client: redis.asyncio.Redis) -> None:
    """Clean up a supplied Redis client during shutdown."""
    closer = getattr(redis_client, "aclose", None)
    if closer is None:
        logger.debug("Redis client does not expose aclose; skipping cleanup")
        return

    try:
        await closer()
        logger.info("Redis connection closed successfully")
    except REDIS_ERRORS as exc:
        raise RedisOperationError("close", original=cast(Exception, exc)) from exc
    except (OSError, RuntimeError) as exc:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        # Connection already closed or system error during cleanup - safe to ignore
        logger.debug("Ignoring redis cleanup error: %s", exc, exc_info=True)
