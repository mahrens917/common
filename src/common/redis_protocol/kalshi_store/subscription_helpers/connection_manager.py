"""
Connection management for KalshiSubscriptionTracker
"""

import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

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
        try:
            redis = await self._connection.get_redis()
            await redis.ping()
        except (
            RuntimeError,
            ConnectionError,
            AttributeError,
        ) as exc:
            self._logger.error("Failed to ensure Redis connection: %s", exc, exc_info=True)
            raise RuntimeError("Failed to establish Redis connection") from exc
        return redis

    async def ensure_connection_or_raise(self, operation: str) -> None:
        """
        Ensure Redis connection or raise an error with operation context.

        Raises:
            RuntimeError: If Redis connection cannot be established
        """
        await self.get_redis()
