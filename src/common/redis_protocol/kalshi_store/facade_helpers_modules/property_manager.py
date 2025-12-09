"""Property manager for facade delegation."""

from typing import Any, Dict, Optional

from redis.asyncio import Redis

from ..connection import RedisConnectionManager


class PropertyManager:
    """Manages property access and delegation for facade."""

    def __init__(self, connection: RedisConnectionManager) -> None:
        self._connection = connection

    @property
    def redis(self) -> Optional[Redis]:
        """Get current Redis connection."""
        return self._connection.redis

    @redis.setter
    def redis(self, value: Optional[Redis]) -> None:
        """Set Redis connection."""
        self._connection.redis = value

    @property
    def initialized(self) -> bool:
        """Get initialization state."""
        return self._connection.initialized

    @initialized.setter
    def initialized(self, value: bool) -> None:
        """Set initialization state."""
        self._connection.initialized = value

    @property
    def pool(self) -> Optional[Any]:
        """Get connection pool."""
        return self._connection.pool

    @pool.setter
    def pool(self, value: Optional[Any]) -> None:
        """Set connection pool."""
        self._connection.pool = value

    @property
    def connection_settings(self) -> Optional[Dict[str, Any]]:
        """Get connection settings."""
        return self._connection.connection_settings

    @connection_settings.setter
    def connection_settings(self, value: Optional[Dict[str, Any]]) -> None:
        """Set connection settings."""
        self._connection.connection_settings = value

    @property
    def connection_settings_logged(self) -> bool:
        """Get connection settings logged state."""
        return self._connection.connection_settings_logged

    @connection_settings_logged.setter
    def connection_settings_logged(self, value: bool) -> None:
        """Set connection settings logged state."""
        self._connection.connection_settings_logged = value
