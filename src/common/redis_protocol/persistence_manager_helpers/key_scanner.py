"""Key scanning and filtering operations for Redis."""

import logging
from typing import TYPE_CHECKING, Any, Dict

from ..error_types import REDIS_ERRORS
from ..typing import ensure_awaitable

if TYPE_CHECKING:
    from ..typing import RedisClient

logger = logging.getLogger(__name__)


class KeyScanner:
    """Manages Redis key scanning and filtering operations."""

    async def get_config_info(self, redis: "RedisClient") -> Dict[str, Any]:
        """
        Get all Redis configuration information.

        Args:
            redis: Redis connection

        Returns:
            Dict containing all Redis config keys and values
        """
        try:
            return await ensure_awaitable(redis.config_get("*"))
        except REDIS_ERRORS:
            logger.exception(f"Failed to get Redis config: ")
            return {}

    async def get_persistence_info(self, redis: "RedisClient") -> Dict[str, Any]:
        """
        Get Redis persistence-specific information.

        Args:
            redis: Redis connection

        Returns:
            Dict containing persistence info
        """
        try:
            return await ensure_awaitable(redis.info("persistence"))
        except REDIS_ERRORS:
            logger.exception(f"Failed to get persistence info: ")
            return {}

    def extract_config_value(self, config_info: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Extract a configuration value.

        Args:
            config_info: Configuration dictionary
            key: Configuration key
            default: Value if key not found

        Returns:
            Configuration value or default
        """
        return config_info.get(key, default)

    def extract_info_value(self, info: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Extract an info value.

        Args:
            info: Info dictionary
            key: Info key
            default: Default value if key not found

        Returns:
            Info value or default
        """
        return info.get(key, default)
