"""
Connection verification for RedisConnectionManager
"""

import asyncio
import logging
from typing import Any

from ...error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class ConnectionVerifier:
    """Verifies Redis connection health"""

    @staticmethod
    async def ping_connection(redis: Any, *, timeout: float = 5.0) -> tuple[bool, bool]:
        """
        Ping Redis connection to verify health

        Args:
            redis: Redis client
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, fatal) where fatal indicates event loop shutdown
        """
        if not hasattr(redis, "ping"):
            return True, False

        try:
            await asyncio.wait_for(redis.ping(), timeout=timeout)
        except asyncio.TimeoutError:  # policy_guard: allow-silent-handler
            logger.warning(
                "Redis ping timed out after %.1fs; connection will be refreshed",
                timeout,
                exc_info=False,
            )
            return False, False
        except REDIS_ERRORS as exc:
            message = str(exc).lower()
            if "event loop is closed" in message:
                logger.debug("Redis ping failed because the event loop is closing: %s", exc, exc_info=False)
                return False, True

            logger.warning("Redis ping failed: %s", exc, exc_info=True)
            return False, False
        else:
            return True, False

    @staticmethod
    async def verify_connection(redis: Any) -> tuple[bool, bool]:
        """
        Verify Redis connection by pinging it

        Args:
            redis: Redis client

        Returns:
            Tuple of (success, fatal) where fatal indicates event loop shutdown
        """
        return await ConnectionVerifier.ping_connection(redis)

    @staticmethod
    async def attach_redis_client(redis_client: Any, *, health_check_timeout: float = 5.0) -> None:
        """
        Validate and attach an externally constructed Redis client

        Args:
            redis_client: Redis client to validate
            health_check_timeout: Timeout for health check ping

        Raises:
            ValueError: If redis_client is invalid
            RuntimeError: If health check fails
        """
        if redis_client is None:
            raise ValueError("attach_redis_client requires a Redis instance")
        if not hasattr(redis_client, "ping"):
            raise ValueError("Provided redis_client must expose an async ping() method")

        try:
            await asyncio.wait_for(redis_client.ping(), timeout=health_check_timeout)
        except asyncio.TimeoutError as exc:  # policy_guard: allow-silent-handler
            raise RuntimeError("Redis client ping timed out during attachment") from exc
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            raise RuntimeError(f"Redis client ping failed during attachment") from exc
