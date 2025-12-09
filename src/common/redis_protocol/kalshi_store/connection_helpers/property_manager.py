"""
Property management for RedisConnectionManager
"""

from typing import Any, Dict, Optional

from redis.asyncio import Redis

from .connection_settings import ConnectionSettingsResolver


class PropertyManager:
    """Manages properties for RedisConnectionManager"""

    def __init__(self, parent: Any):
        """
        Initialize property manager

        Args:
            parent: Parent RedisConnectionManager instance
        """
        self._parent = parent
        self._settings_resolver = ConnectionSettingsResolver(parent=parent)

    @property
    def redis(self) -> Optional[Redis]:
        return self._parent._redis

    @redis.setter
    def redis(self, value: Optional[Redis]) -> None:
        self._parent._redis = value
        if value is None:
            self._parent._pool = None
        else:
            pool = getattr(value, "connection_pool", None)
            if pool is not None:
                self._parent._pool = pool
        self._parent._initialized = value is not None

    @property
    def initialized(self) -> bool:
        return self._parent._initialized

    @initialized.setter
    def initialized(self, value: bool) -> None:
        self._parent._initialized = bool(value)

    @property
    def pool(self) -> Optional[Any]:
        return self._parent._pool

    @pool.setter
    def pool(self, value: Optional[Any]) -> None:
        self._parent._pool = value

    @property
    def connection_settings(self) -> Optional[Dict[str, Any]]:
        return self._settings_resolver.connection_settings

    @connection_settings.setter
    def connection_settings(self, value: Optional[Dict[str, Any]]) -> None:
        self._settings_resolver.connection_settings = value

    @property
    def connection_settings_logged(self) -> bool:
        return self._settings_resolver.connection_settings_logged

    @connection_settings_logged.setter
    def connection_settings_logged(self, value: bool) -> None:
        self._settings_resolver.connection_settings_logged = value

    @property
    def settings_resolver(self) -> ConnectionSettingsResolver:
        return self._settings_resolver
