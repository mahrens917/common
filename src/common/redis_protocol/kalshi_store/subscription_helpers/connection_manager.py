"""
Connection management for KalshiSubscriptionTracker
"""

import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from ...connection_helpers import ensure_or_raise

if TYPE_CHECKING:
    from ..connection import RedisConnectionManager

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Handles Redis connection validation and retrieval"""

    def __init__(self, connection: "RedisConnectionManager", logger_instance: logging.Logger):
        """
        Initialize connection manager

        Args:
            connection: Redis connection manager
            logger_instance: Logger instance
        """
        self._connection = connection
        self._logger = logger_instance

    async def get_redis(self) -> Redis:
        """
        Get Redis connection, ensuring it's properly initialized.

        Returns:
            Redis: Active Redis connection

        Raises:
            RuntimeError: If Redis connection cannot be established
        """
        if not await self._ensure_connection():
            raise RuntimeError("Failed to establish Redis connection")

        return await self._connection.get_redis()

    async def _ensure_connection(self) -> bool:
        """
        Ensure that a healthy Redis client is available.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            redis = await self._connection.get_redis()
            await redis.ping()
        except (RuntimeError, ConnectionError, AttributeError) as exc:
            self._logger.error("Failed to ensure Redis connection: %s", exc, exc_info=True)
            return False
        else:
            return True

    async def ensure_connection_or_raise(self, operation: str) -> None:
        """
        Ensure Redis connection or raise an error with operation context.

        Args:
            operation: Name of the operation being performed

        Raises:
            RuntimeError: If Redis connection cannot be established
        """
        await ensure_or_raise(self._ensure_connection, operation=operation, logger=self._logger)
