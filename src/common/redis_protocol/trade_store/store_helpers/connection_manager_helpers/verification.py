"""Connection verification for TradeStore."""

from __future__ import annotations

from typing import Any

from .base import ConnectionHelperBase


class ConnectionVerificationHelper(ConnectionHelperBase):
    """Handle Redis connection verification operations."""

    async def verify_connection(self, redis: Any) -> tuple[bool, bool]:
        """
        Verify Redis connection is healthy.

        Args:
            redis: Redis client to verify

        Returns:
            Tuple of (success, fatal_error)
        """
        return await self.connection.verify_connection(redis)

    async def ping_connection(self, redis: Any, *, timeout: float = 5.0) -> tuple[bool, bool]:
        """
        Ping Redis connection with timeout.

        Args:
            redis: Redis client to ping
            timeout: Ping timeout in seconds

        Returns:
            Tuple of (success, fatal_error)
        """
        return await self.connection.ping_connection(redis, timeout=timeout)
