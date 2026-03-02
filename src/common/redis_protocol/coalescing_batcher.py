"""Dict-keyed coalescing batcher for Redis pipeline writes."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Generic, TypeVar

from redis.exceptions import RedisError

K = TypeVar("K")
V = TypeVar("V")

logger = logging.getLogger(__name__)

_BATCH_TIME_MS = 200


class CoalescingBatcher(Generic[K, V]):
    """Accumulates updates by key, keeping only the latest value, and flushes every 200ms."""

    def __init__(self, process_batch: Callable[[list[V]], Awaitable[None]], name: str) -> None:
        self._process_batch = process_batch
        self._name = name
        self._pending: dict[K, V] = {}
        self._task: asyncio.Task[None] | None = None
        self._running = False

    def add(self, key: K, value: V) -> None:
        """Store a value by key, overwriting any previous value for the same key."""
        self._pending[key] = value

    async def start(self) -> None:
        """Start the periodic flush loop."""
        self._running = True
        self._task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        """Cancel the flush loop, perform a final flush, and warn on unflushed items."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        flush_results = await asyncio.gather(self._flush(), return_exceptions=True)
        if isinstance(flush_results[0], RedisError):
            logger.warning("%s: final flush failed on shutdown: %s", self._name, flush_results[0])
        if self._pending:
            logger.warning(
                "%s: %d items unflushed on shutdown",
                self._name,
                len(self._pending),
            )

    async def _flush_loop(self) -> None:
        """Sleep 200ms, flush, repeat until stopped."""
        try:
            while self._running:
                await asyncio.sleep(_BATCH_TIME_MS / 1000.0)
                results = await asyncio.gather(self._flush(), return_exceptions=True)
                if isinstance(results[0], RedisError):
                    logger.warning("%s: flush failed, will retry next cycle", self._name)
        except asyncio.CancelledError:
            logger.debug("%s: flush loop cancelled", self._name)
            raise

    async def _flush(self) -> None:
        """Swap pending dict and process. Merge back on RedisError."""
        if not self._pending:
            return
        to_flush = self._pending
        self._pending = {}
        try:
            await self._process_batch(list(to_flush.values()))
        except RedisError:
            to_flush.update(self._pending)
            self._pending = to_flush
            raise
        logger.debug("%s: flushed %d items", self._name, len(to_flush))
