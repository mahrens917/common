"""Batch processing manager for Redis operations with dynamic batch size thresholds."""

import asyncio
import logging
from typing import Awaitable, Callable, Generic, List, TypeVar

from .batch_manager_helpers import BatchCollector, BatchExecutor, BatchTimer

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BatchManager(Generic[T]):
    """Slim coordinator for batch processing operations. Delegates to helper modules for collection, execution, and timing."""

    def __init__(
        self,
        batch_size: int,
        batch_time_ms: int,
        process_batch: Callable[[List[T]], Awaitable[None]],
        name: str = "BatchManager",
    ):
        """Initialize batch manager."""
        self.name = name
        self._lock = asyncio.Lock()
        self._collector = BatchCollector[T](batch_size, name)
        self._executor = BatchExecutor[T](process_batch, name)
        self._timer = BatchTimer(batch_time_ms / 1000.0, self._on_timer_expired, name)

    async def add_item(self, item: T) -> None:
        """Add item to batch and process if thresholds met."""
        async with self._lock:
            should_process = self._collector.add_item(item)
            if len(self._collector.current_batch) == 1:
                self._timer.start(1)
            if should_process:
                await self._process_current_batch("size threshold reached")

    async def _on_timer_expired(self) -> None:
        """Timer callback to process batch on time threshold."""
        async with self._lock:
            if self._collector.has_items():
                await self._process_current_batch("time threshold reached")

    async def _process_current_batch(self, reason: str) -> None:
        """Process current batch and reset state."""
        if not self._collector.has_items():
            return
        batch_size, batch_time = self._collector.get_batch_metrics()
        batch = self._collector.get_batch()
        self._timer.cancel()
        try:
            await self._executor.execute(batch, batch_size, batch_time, reason)
        except asyncio.CancelledError:
            raise
        except (RuntimeError, ValueError, ConnectionError, OSError):
            self._collector.clear()

    async def flush(self) -> None:
        """Process any remaining items in the current batch."""
        async with self._lock:
            if self._collector.has_items():
                await self._process_current_batch("manual flush")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.flush()
        if exc_type:
            logger.error(f"{self.name} exit: {exc_type.__name__}: {exc_val}")
        self._timer.cancel()
        await self._timer.wait_for_cancellation()
