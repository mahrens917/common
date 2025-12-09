"""Lifecycle manager for subscription monitoring."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages start/stop lifecycle for subscription monitoring."""

    def __init__(self, service_name: str):
        """
        Initialize lifecycle manager.

        Args:
            service_name: Name of the service
        """
        self.service_name = service_name
        self._monitoring_task: Optional[asyncio.Task] = None

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

    async def stop_monitoring(self) -> None:
        """Stop subscription monitoring."""
        if self._monitoring_task is not None:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info(f"Stopped {self.service_name} subscription monitoring")

    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring_task is not None
