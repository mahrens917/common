"""
Redis Persistence Management Utility

Manages Redis persistence configuration to ensure trades data survives
Redis server restarts and system reboots. Implements both AOF (Append Only File)
and RDB (Redis Database snapshot) persistence mechanisms.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from .error_types import REDIS_ERRORS
from .persistence_manager_helpers.dependencies_factory import RedisPersistenceManagerDependenciesFactory  # gitleaks:allow
from .persistence_manager_helpers.dependencies_factory import (
    RedisPersistenceManagerDependencies,
)
from .typing import RedisClient

logger = logging.getLogger(__name__)


class RedisPersistenceManager:
    """
    Manages Redis persistence configuration for trades data protection.

    Ensures Redis is configured with both AOF and RDB persistence to protect
    trades data against Redis server restarts and system reboots.
    """

    def __init__(
        self,
        redis: Optional[RedisClient] = None,
        *,
        dependencies: Optional[RedisPersistenceManagerDependencies] = None,
    ):
        """
        Initialize persistence manager.

        Args:
            redis: Redis connection (optional, will be created if not provided)
        """
        self.logger = logger

        deps = dependencies or RedisPersistenceManagerDependenciesFactory.create(redis)  # gitleaks:allow
        self._connection_manager = deps.connection
        self._config_orchestrator = deps.configorchestrator
        self._snapshot_manager = deps.snapshot
        self._key_scanner = deps.keyscanner
        self._serializer = deps.dataserializer
        self._validator = deps.validation

    async def initialize(self) -> bool:
        """Initialize the persistence manager."""
        return await self._connection_manager.ensure_connection()

    async def close(self) -> None:
        """Close the persistence manager and cleanup resources."""
        await self._connection_manager.close()

    async def check_persistence_status(self) -> Dict[str, Any]:
        """Check current Redis persistence configuration status."""
        try:
            redis = await self._connection_manager.get_redis()

            # Get current configuration and persistence info
            config_info = await self._key_scanner.get_config_info(redis)
            persistence_info = await self._key_scanner.get_persistence_info(redis)
            last_save_time = await self._snapshot_manager.get_last_save_time(redis)

            # Build complete status dictionary
            return self._serializer.build_status_dict(config_info, persistence_info, last_save_time)

        except REDIS_ERRORS as exc:
            self.logger.error("Error checking persistence status: %s", exc, exc_info=True)
            return {"error": str(exc)}

    async def configure_persistence(self) -> bool:
        """Configure Redis persistence for trades data protection."""
        redis = await self._connection_manager.get_redis()
        return await self._config_orchestrator.configure_all(redis)

    async def validate_persistence(self) -> Tuple[bool, str]:
        """Validate that Redis persistence is properly configured."""
        try:
            status = await self.check_persistence_status()
            return self._validator.validate_status(status)

        except (
            RuntimeError,
            ValueError,
            OSError,
        ):
            return False, f"Error validating persistence"
        except REDIS_ERRORS:  # policy_guard: allow-silent-handler
            return False, f"Redis error validating persistence"

    async def get_persistence_info(self) -> str:
        """Get human-readable persistence information."""
        try:
            status = await self.check_persistence_status()
            return self._serializer.format_persistence_status(status)

        except (
            RuntimeError,
            ValueError,
            OSError,
        ):
            return f"❌ Error getting persistence info"
        except REDIS_ERRORS:  # policy_guard: allow-silent-handler
            return f"❌ Redis error getting persistence info"


async def ensure_redis_persistence() -> bool:
    """
    Ensure Redis persistence is enabled by validating and configuring if necessary.
    """
    manager = RedisPersistenceManager()
    try:
        await manager.initialize()
        is_valid, _ = await manager.validate_persistence()
        if is_valid:
            return True
        configured = await manager.configure_persistence()
        if not configured:
            return False
        is_valid, _ = await manager.validate_persistence()
        return is_valid
    finally:
        await manager.close()


async def get_redis_persistence_status() -> Dict[str, Any]:
    """
    Fetch the current Redis persistence status payload.
    """
    manager = RedisPersistenceManager()
    try:
        await manager.initialize()
        return await manager.check_persistence_status()
    finally:
        await manager.close()


__all__ = ["RedisPersistenceManager", "ensure_redis_persistence", "get_redis_persistence_status"]
