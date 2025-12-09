"""Connection lifecycle management."""

import asyncio
import contextlib
import logging
from typing import Optional


class ConnectionLifecycleManager:
    """Manages connection lifecycle tasks."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.health_check_task: Optional[asyncio.Task] = None
        self.reconnection_task: Optional[asyncio.Task] = None
        self.shutdown_requested = False
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def start_health_monitoring(self, monitor_func, interval: float) -> None:
        """Start health monitoring task."""
        self.logger.info("Starting health monitoring")

        while not self.shutdown_requested:
            try:
                await monitor_func()
                await asyncio.sleep(interval)
            except (ConnectionError, TimeoutError, RuntimeError):
                self.logger.exception(f"Health monitoring error: ")
                raise

    def start_reconnection_task(self, reconnect_func) -> None:
        """Start reconnection task if not already running."""
        if not self.reconnection_task or self.reconnection_task.done():
            self.logger.info("Starting reconnection task")
            self.reconnection_task = asyncio.create_task(reconnect_func())

    async def stop(self, cleanup_func) -> None:
        """Stop lifecycle tasks and cleanup."""
        self.logger.info("Stopping connection lifecycle")
        self.shutdown_requested = True

        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.health_check_task

        if self.reconnection_task and not self.reconnection_task.done():
            self.reconnection_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.reconnection_task

        await cleanup_func()
