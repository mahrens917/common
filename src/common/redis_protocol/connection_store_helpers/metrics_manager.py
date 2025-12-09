"""
Service metrics management for ConnectionStore
"""

import json
import logging
from typing import Any, Dict, Optional

from ..error_types import JSON_ERRORS, REDIS_ERRORS, SERIALIZATION_ERRORS
from ..typing import ensure_awaitable

logger = logging.getLogger(__name__)


class MetricsManager:
    """Manages service-specific metrics storage"""

    def __init__(self, redis_getter):
        """
        Initialize metrics manager

        Args:
            redis_getter: Async function that returns Redis client
        """
        self._get_client = redis_getter

    async def store_service_metrics(self, service_name: str, metrics: Dict[str, Any]) -> bool:
        """
        Store service-specific metrics for monitoring.

        Args:
            service_name: Name of the service
            metrics: Dictionary of metrics to store

        Returns:
            True if stored successfully, False otherwise
        """
        client = await self._get_client()

        try:
            metrics_json = json.dumps(metrics)
        except SERIALIZATION_ERRORS:
            logger.error(
                "Failed to serialise connection metrics for %s",
                service_name,
                exc_info=True,
            )
            return False

        metrics_key = f"connection_metrics:{service_name}"
        try:
            await ensure_awaitable(client.set(metrics_key, metrics_json))
            await ensure_awaitable(client.expire(metrics_key, 3600))
            logger.debug("Stored connection metrics for %s", service_name)
        except REDIS_ERRORS:
            logger.error(
                "Failed to store connection metrics for %s",
                service_name,
                exc_info=True,
            )
            return False
        else:
            return True

    async def get_service_metrics(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get service-specific metrics.

        Args:
            service_name: Name of the service

        Returns:
            Dictionary of metrics if found, None otherwise
        """
        client = await self._get_client()
        metrics_key = f"connection_metrics:{service_name}"

        try:
            metrics_json = await ensure_awaitable(client.get(metrics_key))
        except REDIS_ERRORS:
            logger.error(
                "Failed to get connection metrics for %s",
                service_name,
                exc_info=True,
            )
            return None

        if not metrics_json:
            return None

        try:
            return json.loads(metrics_json)
        except JSON_ERRORS:
            logger.error(
                "Failed to decode connection metrics for %s",
                service_name,
                exc_info=True,
            )
            return None
