"""
Connection Wrapper - Redis connection helper for KalshiMarketReader

Provides connection management utilities.
"""

import logging

from redis.asyncio import Redis

from ...connection_helpers import ensure_or_raise

logger = logging.getLogger(__name__)


class ReaderConnectionWrapper:
    """Wraps connection manager for reader operations"""

    def __init__(self, connection_manager, logger_instance: logging.Logger):
        """
        Initialize connection wrapper

        Args:
            connection_manager: RedisConnectionManager instance
            logger_instance: Logger instance
        """
        self._connection = connection_manager
        self.logger = logger_instance

    async def get_redis(self) -> Redis:
        """Get Redis connection"""
        return await self._connection.get_redis()

    async def ensure_connection(self) -> bool:
        """Ensure Redis connection is ready"""
        return await self._connection.ensure_connection()

    async def ensure_or_raise(self, operation: str) -> Redis:
        """
        Ensure connection or raise error

        Args:
            operation: Operation name for error message

        Returns:
            Redis connection

        Raises:
            RuntimeError: If connection cannot be established
        """
        await ensure_or_raise(self.ensure_connection, operation=operation, logger=self.logger)
        return await self.get_redis()
