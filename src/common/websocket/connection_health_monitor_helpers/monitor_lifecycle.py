"""Monitor lifecycle management."""

import asyncio
import logging
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


class MonitorLifecycle:
    """Manages monitoring task lifecycle."""

    def __init__(self, service_name: str, health_check_interval_seconds: int):
        """
        Initialize monitor lifecycle.

        Args:
            service_name: Name of the service
            health_check_interval_seconds: Interval between health checks
        """
        self.service_name = service_name
        self.health_check_interval_seconds = health_check_interval_seconds
        self._monitoring_task: Optional[asyncio.Task] = None

    async def start_monitoring(self, check_health_callback: Callable[[], Awaitable[None]]) -> None:
        """
        Start continuous health monitoring.

        Args:
            check_health_callback: Async callback to perform health check
        """
        if self._monitoring_task is not None:
            logger.warning(f"{self.service_name} health monitoring already started")
            return

        logger.info(f"Starting {self.service_name} connection health monitoring")
        self._monitoring_task = asyncio.create_task(self._monitor_loop(check_health_callback))

    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        if self._monitoring_task is not None:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:  # policy_guard: allow-silent-handler
                pass
            self._monitoring_task = None
            logger.info(f"Stopped {self.service_name} connection health monitoring")

    async def _monitor_loop(self, check_health_callback: Callable[[], Awaitable[None]]) -> None:
        """Main monitoring loop."""
        try:
            while True:
                await asyncio.sleep(self.health_check_interval_seconds)
                await check_health_callback()
        except asyncio.CancelledError:  # policy_guard: allow-silent-handler
            logger.info(f"{self.service_name} health monitoring cancelled")
            raise
        except ConnectionError:  # policy_guard: allow-silent-handler
            logger.exception("Fatal error in %s health monitoring", self.service_name)
            raise
