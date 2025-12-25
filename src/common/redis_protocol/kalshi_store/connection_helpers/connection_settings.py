"""
Connection settings resolution for RedisConnectionManager
"""

import logging
from typing import Any, Dict, Optional

from ... import config as redis_config

logger = logging.getLogger(__name__)


class ConnectionSettingsResolver:
    """Resolves and manages Redis connection settings"""

    def __init__(self, parent: Any = None):
        """Initialize connection settings resolver

        Args:
            parent: Optional parent connection manager to get logger from
        """
        self._connection_settings: Optional[Dict[str, Any]] = None
        self._connection_settings_logged = False
        self._parent = parent

    def resolve_connection_settings(self) -> Dict[str, Any]:
        """Resolve Redis connection settings from config"""
        if self._connection_settings is None:
            # Import kalshi_store module to pick up any monkeypatched values
            import importlib

            kalshi_store_module = importlib.import_module("common.redis_protocol.kalshi_store")

            settings: Dict[str, Any] = {
                "host": getattr(kalshi_store_module, "REDIS_HOST", redis_config.REDIS_HOST),
                "port": getattr(kalshi_store_module, "REDIS_PORT", redis_config.REDIS_PORT),
                "db": getattr(kalshi_store_module, "REDIS_DB", redis_config.REDIS_DB),
                "password": getattr(kalshi_store_module, "REDIS_PASSWORD", redis_config.REDIS_PASSWORD),
                "ssl": getattr(kalshi_store_module, "REDIS_SSL", redis_config.REDIS_SSL),
            }
            self._connection_settings = settings

        if not self._connection_settings_logged:
            masked = dict(self._connection_settings)
            if masked.get("password"):
                masked["password"] = "***"
            # Use parent logger if available, otherwise use module logger
            active_logger = getattr(self._parent, "_logger", logger) if self._parent else logger
            active_logger.info("Resolved Redis connection settings: %s", masked)
            self._connection_settings_logged = True

        return self._connection_settings

    @property
    def connection_settings(self) -> Optional[Dict[str, Any]]:
        return self._connection_settings

    @connection_settings.setter
    def connection_settings(self, value: Optional[Dict[str, Any]]) -> None:
        self._connection_settings = value

    @property
    def connection_settings_logged(self) -> bool:
        return self._connection_settings_logged

    @connection_settings_logged.setter
    def connection_settings_logged(self, value: bool) -> None:
        self._connection_settings_logged = bool(value)
