"""Lifecycle management for background scanning."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages process monitor lifecycle (start/stop)."""

    def __init__(self, background_worker, shutdown_event: asyncio.Event):
        self.background_worker = background_worker
        self.shutdown_event = shutdown_event
        self._background_task: Optional[asyncio.Task] = None

    async def start_background_scanning(self, scan_interval_seconds: int) -> None:
        """
        Start background task to periodically refresh process cache.

        Args:
            scan_interval_seconds: Interval between scans
        """
        if self._background_task is not None:
            return

        self.shutdown_event.clear()
        self._background_task = asyncio.create_task(self.background_worker.run_scan_loop())
        logger.info(f"Started process monitor background scanning (interval: {scan_interval_seconds}s)")

    async def stop_background_scanning(self) -> None:
        """Stop background process scanning."""
        if self._background_task is None:
            return

        logger.info("Stopping process monitor background scanning")
        self.shutdown_event.set()

        try:
            await asyncio.wait_for(self._background_task, timeout=2.0)
        except asyncio.TimeoutError:
            self._background_task.cancel()

        self._background_task = None
        logger.info("Process monitor background scanning stopped")

    def is_running(self) -> bool:
        """Check if background scanning is running."""
        return self._background_task is not None
