"""Connection state management for TradeStore."""

from typing import Any, Optional

from redis.asyncio import Redis

from ....error_types import REDIS_ERRORS
from ....kalshi_store.connection import RedisConnectionManager
from .base import ConnectionHelperBase


class ConnectionStateHelper(ConnectionHelperBase):
    """Handle Redis connection state management."""

    def ensure_connection_manager(self) -> None:
        """Ensure connection manager is properly initialized."""
        if not hasattr(self, "_connection"):
            self._connection = RedisConnectionManager(logger=self.logger, redis=None)

    def reset_connection_state(self) -> None:
        """Reset connection state for retry."""
        self.connection.reset_connection_state()

    async def close_redis_client(self, redis_client: Any, redis_setter=None) -> None:
        """
        Close a Redis client instance.

        Args:
            redis_client: Client to close
            redis_setter: Optional setter for redis property
        """
        await self.connection.close_redis_client(redis_client)

    async def close(self, redis_setter) -> None:
        """
        Close Redis connection cleanly.

        Args:
            redis_setter: Callable to set redis property to None

        Raises:
            TradeStoreShutdownError: If close fails
        """
        self.ensure_connection_manager()
        try:
            await self.connection.close()
        except REDIS_ERRORS as exc:
            self.logger.error("Error closing TradeStore Redis connection: %s", exc, exc_info=True)
            from ...errors import TradeStoreShutdownError

            raise TradeStoreShutdownError("Failed to close Redis connection cleanly") from exc
        finally:
            redis_setter(None)
            self.connection.pool = None
            self.connection.initialized = False

    @property
    def redis(self) -> Optional[Redis]:
        """Get current Redis client from connection manager."""
        return self.connection.redis

    @redis.setter
    def redis(self, value: Optional[Redis]) -> None:
        """Set Redis client in connection manager."""
        self.connection.redis = value
