"""Background scanning worker."""

import asyncio
import logging
from typing import Callable

import psutil

logger = logging.getLogger(__name__)


class BackgroundScanWorker:
    """Manages background process scanning loop."""

    def __init__(
        self,
        scan_interval_seconds: int,
        perform_incremental_scan: Callable,
        shutdown_event: asyncio.Event,
    ):
        self.scan_interval_seconds = scan_interval_seconds
        self.perform_incremental_scan = perform_incremental_scan
        self.shutdown_event = shutdown_event

    async def run_scan_loop(self):
        """Background loop to periodically refresh process cache."""
        logger.debug("Process monitor background scan loop started")

        while not self.shutdown_event.is_set():
            try:
                await self.perform_incremental_scan()

                # Wait for next scan or shutdown signal
                try:
                    await asyncio.wait_for(self.shutdown_event.wait(), timeout=self.scan_interval_seconds)
                    break  # Shutdown requested
                except asyncio.TimeoutError:  # Transient network/connection failure  # policy_guard: allow-silent-handler
                    continue  # Normal timeout, continue scanning

            except (  # policy_guard: allow-silent-handler
                psutil.Error,
                asyncio.CancelledError,
                OSError,
                RuntimeError,
            ):
                logger.exception(f"Error in process monitor background loop: ")
                await asyncio.sleep(self.scan_interval_seconds)

        logger.debug("Process monitor background scan loop stopped")
