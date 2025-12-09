from __future__ import annotations

"""
Asynchronous CPU monitoring utility.

Provides a high-level interface for sampling CPU usage without blocking the
event loop by running measurements inside a lightweight background task.
"""


import asyncio
import contextlib
import logging
from typing import Optional

from .simple_system_metrics import get_cpu_percent as _sync_cpu_percent

logger = logging.getLogger(__name__)


class CpuMonitorError(RuntimeError):
    """Raised when the CPU monitor cannot continue sampling CPU usage."""


class CpuMonitor:
    """
    Periodically samples CPU usage in the background and exposes the latest
    value through an async-friendly API.
    """

    def __init__(self, sample_interval: float = 1.0) -> None:
        self.sample_interval = max(sample_interval, 0.1)
        self._current_cpu_percent: Optional[float] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._lock = asyncio.Lock()
        self._running = False
        self._initialized = False

    async def initialize(self) -> None:
        """Prime the monitor with an initial CPU reading."""

        if self._initialized:
            return

        self._current_cpu_percent = await self._read_cpu_percent()
        self._initialized = True
        logger.debug("CpuMonitor initialized with %.2f%%", self._current_cpu_percent)

    async def start_background_updates(self) -> None:
        """Start the background sampling task."""

        if not self._initialized:
            raise RuntimeError("CpuMonitor.initialize() must be called before starting updates")

        if self._task and not self._task.done():
            return

        self._running = True
        self._task = asyncio.create_task(self._update_loop(), name="cpu-monitor-loop")
        logger.debug("CpuMonitor background updates started")

    async def stop_background_updates(self) -> None:
        """Stop the background sampling task."""

        self._running = False
        if self._task is None:
            return

        self._task.cancel()
        try:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        finally:
            self._task = None
            logger.debug("CpuMonitor background updates stopped")

    async def get_cpu_percent(self) -> float:
        """Return the latest sampled CPU percentage."""

        if not self._initialized:
            raise RuntimeError("CpuMonitor must be initialized before reading values")

        async with self._lock:
            if self._current_cpu_percent is not None:
                return self._current_cpu_percent

        # If we somehow lost our cached value, refresh synchronously.
        value = await self._read_cpu_percent()
        async with self._lock:
            self._current_cpu_percent = value
        return value

    async def _update_loop(self) -> None:
        try:
            while self._running:
                value = await self._read_cpu_percent()
                async with self._lock:
                    self._current_cpu_percent = value
                if not self._running:
                    break
                await asyncio.sleep(self.sample_interval)
        except asyncio.CancelledError:
            logger.debug("CpuMonitor update loop cancelled")
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            logger.exception("CpuMonitor update loop terminated unexpectedly")
            raise CpuMonitorError("CpuMonitor update loop terminated unexpectedly") from exc
        finally:
            self._running = False

    async def _read_cpu_percent(self) -> float:
        """Run the synchronous CPU sampling in a worker thread."""

        return await asyncio.to_thread(_sync_cpu_percent)
