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


"""Connection settings resolution for TradeStore."""

import importlib
from typing import Any, Dict

from .... import config as redis_config
from .base import ConnectionHelperBase


class ConnectionSettingsHelper(ConnectionHelperBase):
    """Handle Redis connection settings resolution."""

    def resolve_connection_settings(self) -> Dict[str, Any]:
        """
        Resolve Redis connection settings with module-level overrides.

        Returns:
            Dictionary of connection settings
        """
        package = importlib.import_module("common.redis_protocol.trade_store")
        needs_logging_reset = self.connection.connection_settings is None
        self.connection.connection_settings = {
            "host": getattr(package, "REDIS_HOST", redis_config.REDIS_HOST),
            "port": getattr(package, "REDIS_PORT", redis_config.REDIS_PORT),
            "db": getattr(package, "REDIS_DB", redis_config.REDIS_DB),
            "password": getattr(package, "REDIS_PASSWORD", redis_config.REDIS_PASSWORD),
            "ssl": getattr(package, "REDIS_SSL", redis_config.REDIS_SSL),
        }
        if needs_logging_reset:
            self.connection.connection_settings_logged = False
        return self.connection.connection_settings
