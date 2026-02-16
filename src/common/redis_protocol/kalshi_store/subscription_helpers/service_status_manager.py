"""
Service status management for KalshiSubscriptionTracker
"""

import logging
from typing import Any, Optional

from ...error_types import REDIS_ERRORS
from ..utils_coercion import coerce_mapping as _canonical_coerce_mapping

logger = logging.getLogger(__name__)


class ServiceStatusManager:
    """Manages service status in Redis"""

    def __init__(self, redis_getter, service_status_key: str):
        """
        Initialize service status manager

        Args:
            redis_getter: Async function that returns Redis client
            service_status_key: Redis key for service status hash
        """
        self._get_redis = redis_getter
        self.service_status_key = service_status_key

    @staticmethod
    def _string_or_default(value: Any, fill_value: str = "") -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", "ignore")
        return fill_value

    async def update_service_status(self, service: str, status: Any) -> bool:
        """
        Update service status using unified status hash

        Args:
            service: Service name (e.g., 'kalshi')
            status: Status dictionary

        Returns:
            True if successful

        Raises:
            RuntimeError: If Redis connection cannot be established
            Exception: If status update fails
        """
        redis = await self._get_redis()

        # Extract status value from dictionary or use as-is if string
        if isinstance(status, dict):
            status_mapping = _canonical_coerce_mapping(status)
            status_value = self._string_or_default(status_mapping.get("status"), "unknown")
        else:
            status_value = self._string_or_default(status, "unknown")

        try:
            await redis.hset(self.service_status_key, service, status_value)
        except REDIS_ERRORS as exc:
            logger.error("Error updating %s status: %s", service, exc, exc_info=True)
            raise
        logger.debug("Updated %s status to: %s", service, status_value)
        return True

    async def get_service_status(self, service: str) -> Optional[str]:
        """
        Get service status from unified status hash

        Args:
            service: Service name (e.g., 'kalshi')

        Returns:
            Status string or None if not found
        """
        try:
            redis = await self._get_redis()
            status_value = await redis.hget(self.service_status_key, service)
            if status_value:
                return status_value

            else:
                return None
        except REDIS_ERRORS as exc:
            logger.error("Error getting %s status: %s", service, exc, exc_info=True)
            raise
