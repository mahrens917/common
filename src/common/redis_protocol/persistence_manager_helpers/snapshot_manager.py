"""Snapshot save/restore operations for Redis persistence."""

import logging
from typing import TYPE_CHECKING

from ..error_types import REDIS_ERRORS
from ..typing import ensure_awaitable

if TYPE_CHECKING:
    from ..typing import RedisClient

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages Redis snapshot (RDB) save and restore operations."""

    async def force_background_save(self, redis: "RedisClient") -> bool:
        """
        Force an immediate background save to create RDB file.

        Args:
            redis: Redis connection

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            await ensure_awaitable(redis.bgsave())
            logger.info("Initiated background save for initial RDB file")
        except REDIS_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.warning("Failed to initiate background save: %s", exc)
            return False
        else:
            return True

    async def get_last_save_time(self, redis: "RedisClient") -> int:
        """
        Get the timestamp of the last successful save.

        Args:
            redis: Redis connection

        Returns:
            int: Unix timestamp of last save
        """
        return await ensure_awaitable(redis.lastsave())

    async def configure_save_points(self, redis: "RedisClient", save_config: str) -> bool:
        """
        Configure RDB save points.

        Args:
            redis: Redis connection
            save_config: Space-separated save points (e.g., "900 1 300 10 60 10000")

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Clear existing save points first
            await ensure_awaitable(redis.config_set("save", ""))

            # Set new save points
            save_points = save_config.split()
            for i in range(0, len(save_points), 2):
                if i + 1 < len(save_points):
                    seconds = save_points[i]
                    changes = save_points[i + 1]
                    await ensure_awaitable(redis.config_set("save", f"{seconds} {changes}"))

            logger.debug(f"Configured RDB save points: {save_config}")

        except REDIS_ERRORS:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.warning(f"Failed to configure save points")
            return False
        else:
            return True
