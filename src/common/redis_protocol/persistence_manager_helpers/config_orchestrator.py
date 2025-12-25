"""Configuration orchestration for Redis persistence."""

import logging
from typing import TYPE_CHECKING

from ..error_types import REDIS_ERRORS

if TYPE_CHECKING:
    from ..typing import RedisClient
    from .persistence_coordinator import PersistenceCoordinator
    from .snapshot_manager import SnapshotManager

logger = logging.getLogger(__name__)


class ConfigOrchestrator:
    """Orchestrates the complete persistence configuration process."""

    def __init__(
        self,
        coordinator: "PersistenceCoordinator",
        snapshot_manager: "SnapshotManager",
    ):
        """
        Initialize config orchestrator.

        Args:
            coordinator: Persistence coordinator
            snapshot_manager: Snapshot manager
        """
        self._coordinator = coordinator
        self._snapshot_manager = snapshot_manager

    async def configure_all(self, redis: "RedisClient") -> bool:
        """
        Execute complete persistence configuration process.

        Args:
            redis: Redis connection

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Configuring Redis persistence for trades data protection...")

            # Create data directory
            if not await self._coordinator.ensure_data_directory():
                return False

            # Apply runtime configuration
            config_applied, config_failed, _immutable_skipped = await self._coordinator.apply_runtime_config(redis)

            # Configure save points separately (special handling required)
            save_config = "900 1 300 10 60 10000"
            if await self._snapshot_manager.configure_save_points(redis, save_config):
                config_applied += 1
            else:
                config_failed += 1

            # Log immutable configs
            self._coordinator.log_immutable_configs()

            # Persist configuration to disk
            await self._coordinator.persist_config_to_disk(redis)

            # Force initial save
            await self._snapshot_manager.force_background_save(redis)

            success = config_failed == 0
            logger.info(f"Redis persistence configuration completed: {config_applied} applied, " f"{config_failed} failed")

        except REDIS_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.error("Error configuring Redis persistence: %s", exc, exc_info=True)
            return False
        else:
            return success
