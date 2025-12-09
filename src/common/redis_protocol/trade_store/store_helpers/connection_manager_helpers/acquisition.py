"""Connection acquisition logic for TradeStore."""

from redis.asyncio import Redis

from ...errors import TradeStoreError
from .base import ConnectionHelperBase


class ConnectionAcquisitionHelper(ConnectionHelperBase):
    """Handle Redis connection acquisition and validation."""

    async def get_redis(self, redis_property_getter, ensure_connection_func, ping_func) -> Redis:
        """
        Get Redis client with automatic reconnection if needed.

        Args:
            redis_property_getter: Callable that returns current redis property
            ensure_connection_func: Callable to ensure connection
            ping_func: Callable to ping connection

        Returns:
            Active Redis client

        Raises:
            TradeStoreError: If connection cannot be established
        """
        redis_client = redis_property_getter()

        if redis_client is None or not self.connection.initialized:
            self.logger.warning(
                "TradeStore Redis state corruption detected - redis: %s, initialized: %s",
                redis_client is not None,
                self.connection.initialized,
            )

        initial_result = await ensure_connection_func()
        redis_client = redis_property_getter()

        if redis_client is None:
            if not await ensure_connection_func():
                message = self._connection_failure_message(initial_result)
                raise TradeStoreError(message)
            redis_client = redis_property_getter()
            if redis_client is None:
                message = self._connection_failure_message(initial_result)
                raise TradeStoreError(message)

        ok, fatal = await ping_func(redis_client)
        if not ok:
            if fatal or not await ensure_connection_func():
                raise TradeStoreError("Failed to re-establish Redis connection")
            redis_client = redis_property_getter()
            if redis_client is None:
                raise TradeStoreError("Failed to re-establish Redis connection")

        return redis_client

    @staticmethod
    def _connection_failure_message(attempted_reconnect: bool) -> str:
        """Generate connection failure message."""
        if attempted_reconnect:
            return "Failed to re-establish Redis connection"
        return "Failed to establish Redis connection"
