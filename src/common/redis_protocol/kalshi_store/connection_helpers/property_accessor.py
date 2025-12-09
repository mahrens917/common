from __future__ import annotations

"""
Property accessors for RedisConnectionManager.

Centralizes all property getters/setters to reduce boilerplate.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from redis.asyncio import Redis

if TYPE_CHECKING:
    from ..connection import RedisConnectionManager


class PropertyAccessor:
    """Provides property access methods for RedisConnectionManager."""

    def __init__(self, manager: RedisConnectionManager) -> None:
        self._manager = manager

    @property
    def redis(self) -> Optional[Redis]:
        """Get current Redis connection."""
        return self._manager.property_manager.redis

    @redis.setter
    def redis(self, value: Optional[Redis]) -> None:
        """Set Redis connection."""
        self._manager.property_manager.redis = value

    @property
    def initialized(self) -> bool:
        """Get initialization state."""
        return self._manager.property_manager.initialized

    @initialized.setter
    def initialized(self, value: bool) -> None:
        """Set initialization state."""
        self._manager.property_manager.initialized = value

    @property
    def pool(self) -> Optional[Any]:
        """Get connection pool."""
        return self._manager.property_manager.pool

    @pool.setter
    def pool(self, value: Optional[Any]) -> None:
        """Set connection pool."""
        self._manager.property_manager.pool = value

    @property
    def connection_settings(self) -> Optional[Dict[str, Any]]:
        """Get connection settings."""
        return self._manager.property_manager.connection_settings

    @connection_settings.setter
    def connection_settings(self, value: Optional[Dict[str, Any]]) -> None:
        """Set connection settings."""
        self._manager.property_manager.connection_settings = value

    @property
    def connection_settings_logged(self) -> bool:
        """Get connection settings logged state."""
        return self._manager.property_manager.connection_settings_logged

    @connection_settings_logged.setter
    def connection_settings_logged(self, value: bool) -> None:
        """Set connection settings logged state."""
        self._manager.property_manager.connection_settings_logged = value
