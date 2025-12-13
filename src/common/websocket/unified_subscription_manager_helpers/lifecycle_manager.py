"""Lifecycle manager for subscription monitoring."""

import asyncio
import logging
from typing import Optional

from common.websocket.monitoring_task_mixin import MonitoringTaskMixin

logger = logging.getLogger(__name__)


class LifecycleManager(MonitoringTaskMixin):
    """Manages start/stop lifecycle for subscription monitoring."""

    def __init__(self, service_name: str):
        """
        Initialize lifecycle manager.

        Args:
            service_name: Name of the service
        """
        self.service_name = service_name
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_label = "subscription monitoring"

    async def start_monitoring(self, monitor_coro) -> None:
        """
        Start Redis pub/sub monitoring.

        Args:
            monitor_coro: Coroutine to run for monitoring
        """
        if self._monitoring_task is not None:
            logger.warning(f"{self.service_name} subscription monitoring already started")
            return

        logger.info(f"Starting {self.service_name} subscription monitoring")
        self._monitoring_task = asyncio.create_task(monitor_coro)

    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring_task is not None
