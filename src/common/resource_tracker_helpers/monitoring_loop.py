"""Per-second monitoring loop for resource tracking."""

import asyncio
import logging
import time
from collections import deque
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class MonitoringLoop:
    """Manages per-second resource monitoring."""

    def __init__(self, cpu_tracker, ram_tracker, stop_event: asyncio.Event | None = None):
        """
        Initialize monitoring loop.

        Args:
            cpu_tracker: CpuTracker instance
            ram_tracker: RamTracker instance
            stop_event: Optional shared stop event supplied by ResourceTracker
        """
        self.cpu_tracker = cpu_tracker
        self.ram_tracker = ram_tracker

        # Per-second tracking for max calculation
        self._cpu_readings = deque(maxlen=60)
        self._ram_readings = deque(maxlen=60)
        self._monitoring_task = None
        self._stop_monitoring = stop_event or asyncio.Event()

    async def start(self, get_cpu_ram_func: Callable):
        """
        Start per-second monitoring task.

        Args:
            get_cpu_ram_func: Async function that returns (cpu_percent, ram_mb) tuple
        """
        if self._monitoring_task is not None:
            return

        self._stop_monitoring.clear()
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(get_cpu_ram_func))
        logger.debug("Started per-second resource monitoring task")

    async def stop(self):
        """Stop per-second monitoring task."""
        if self._monitoring_task is None:
            return

        self._stop_monitoring.set()
        try:
            await asyncio.wait_for(self._monitoring_task, timeout=2.0)
        except asyncio.TimeoutError:
            self._monitoring_task.cancel()
        self._monitoring_task = None
        logger.debug("Stopped per-second resource monitoring task")

    async def _monitoring_loop(self, get_cpu_ram_func: Callable):
        """Internal monitoring loop that runs every second."""
        while not self._stop_monitoring.is_set():
            try:
                cpu_percent, ram_mb = await get_cpu_ram_func()
                current_time = time.time()

                self._cpu_readings.append((current_time, cpu_percent))
                self._ram_readings.append((current_time, ram_mb))

                try:
                    await self.cpu_tracker.record_cpu_usage(cpu_percent)
                    await self.ram_tracker.record_ram_usage(ram_mb)
                except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # policy_guard: allow-silent-handler
                    logger.exception("Error storing per-second data to Redis")
                    raise RuntimeError("Failed to store resource metrics to Redis") from exc

            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # policy_guard: allow-silent-handler
                logger.exception("Error in per-second monitoring")
                raise

            try:
                await asyncio.wait_for(self._stop_monitoring.wait(), timeout=1.0)
                break
            except asyncio.TimeoutError:  # policy_guard: allow-silent-handler
                continue

    def get_max_cpu_last_minute(self) -> Optional[float]:
        """Get maximum CPU usage over the last minute."""
        if not self._cpu_readings:
            return None
        return max(reading[1] for reading in self._cpu_readings)

    def get_max_ram_last_minute(self) -> Optional[float]:
        """Get maximum RAM usage over the last minute."""
        if not self._ram_readings:
            return None
        return max(reading[1] for reading in self._ram_readings)

    async def __call__(self, get_cpu_ram_func: Callable):
        """Allow tests to await the internal monitoring coroutine directly."""
        await self._monitoring_loop(get_cpu_ram_func)
