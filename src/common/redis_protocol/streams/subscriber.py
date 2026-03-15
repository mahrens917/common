"""Generic Redis Streams subscriber with consumer group support.

Uses Redis Streams for persistent, at-least-once message delivery.
Messages survive subscriber restarts.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Tuple, Union

from .consumer_group import reset_group_position
from .subscriber_helpers.consumer import MAX_STREAM_RETRIES, consume_stream_queue
from .subscriber_helpers.lifecycle import cancel_task, cancel_tasks, send_stop_sentinels
from .subscriber_helpers.reader import stream_read_loop
from .subscriber_helpers.recovery import (
    discard_all_pending,
    initialize_consumer_group,
)

logger = logging.getLogger(__name__)

MessageHandler = Callable[[str, dict], Awaitable[None]]

_DEFAULT_BLOCK_MS = 5000
_DEFAULT_BATCH_SIZE = 100
_DEFAULT_QUEUE_SIZE = 10000
_DEFAULT_NUM_CONSUMERS = 1


@dataclass
class StreamConfig:
    """Configuration for a stream subscriber."""

    stream_name: str
    group_name: str
    consumer_name: str
    identifier_field: str = "ticker"
    block_ms: int = _DEFAULT_BLOCK_MS
    batch_size: int = _DEFAULT_BATCH_SIZE
    queue_size: int = _DEFAULT_QUEUE_SIZE
    num_consumers: int = _DEFAULT_NUM_CONSUMERS
    coalesce: bool = False
    max_concurrent_dispatches: int = 1
    handler_timeout_s: float = 0


@dataclass
class SubscriberHealthInfo:
    """Snapshot of subscriber health for external monitoring."""

    last_processed_time: float
    messages_processed: int
    queue_size: int
    queue_maxsize: int
    running: bool


class RedisStreamSubscriber:
    """Generic Redis Streams subscriber with consumer group support.

    Uses an internal asyncio.Queue to decouple stream reading from
    message processing.
    """

    def __init__(
        self,
        redis_client: Any,
        on_message: MessageHandler,
        *,
        config: StreamConfig,
        subscriber_name: str = "stream-subscriber",
    ) -> None:
        self._redis_client = redis_client
        self._on_message = on_message
        self._config = config
        self._subscriber_name = subscriber_name
        self._running = False
        self._reader_task: Optional[asyncio.Task[None]] = None
        self._consumer_tasks: list[asyncio.Task[None]] = []
        self._queue: asyncio.Queue[Union[Tuple[str, str, dict], None]] = asyncio.Queue(maxsize=config.queue_size)
        self._retry_counts: dict[str, int] = {}
        self._last_processed_time: float = 0.0
        self._messages_processed: int = 0

    @property
    def running(self) -> bool:
        """Whether the subscriber is running."""
        return self._running

    @property
    def reader_task(self) -> Optional[asyncio.Task[None]]:
        """Expose underlying reader task for health monitoring."""
        return self._reader_task

    @property
    def consumer_tasks(self) -> list[asyncio.Task[None]]:
        """Expose consumer tasks for health monitoring."""
        return self._consumer_tasks

    def health_info(self) -> SubscriberHealthInfo:
        """Return a snapshot of subscriber health metrics."""
        return SubscriberHealthInfo(
            last_processed_time=self._last_processed_time,
            messages_processed=self._messages_processed,
            queue_size=self._queue.qsize(),
            queue_maxsize=self._queue.maxsize,
            running=self._running,
        )

    def record_processed(self) -> None:
        """Record that a message was successfully processed."""
        self._last_processed_time = time.monotonic()
        self._messages_processed += 1

    async def start(self) -> None:
        """Start the stream subscriber."""
        if self._running:
            return

        await initialize_consumer_group(
            self._redis_client,
            self._config.stream_name,
            self._config.group_name,
        )

        discarded = await discard_all_pending(
            self._redis_client,
            self._config.stream_name,
            self._config.group_name,
            self._config.consumer_name,
        )
        if discarded:
            logger.info("%s discarded %d stale pending entries", self._subscriber_name, discarded)

        await reset_group_position(
            self._redis_client,
            self._config.stream_name,
            self._config.group_name,
        )

        self._running = True
        self._reader_task = asyncio.create_task(self._read_loop(), name=f"{self._subscriber_name}-reader")
        self._consumer_tasks = [
            asyncio.create_task(self._consume_queue(), name=f"{self._subscriber_name}-consumer-{i}")
            for i in range(self._config.num_consumers)
        ]
        logger.info(
            "%s started on stream %s (group=%s, consumer=%s)",
            self._subscriber_name,
            self._config.stream_name,
            self._config.group_name,
            self._config.consumer_name,
        )

    async def stop(self) -> None:
        """Stop the stream subscriber and clean up."""
        self._running = False
        send_stop_sentinels(self._queue, len(self._consumer_tasks), self._subscriber_name)
        await cancel_task(self._reader_task)
        self._reader_task = None
        await cancel_tasks(self._consumer_tasks)
        self._consumer_tasks = []
        self._retry_counts.clear()
        logger.info("%s stopped", self._subscriber_name)

    async def _read_loop(self) -> None:
        """Read entries from the stream and enqueue for processing."""
        await stream_read_loop(
            lambda: self._running,
            self._redis_client,
            self._config,
            self._queue,
            self._subscriber_name,
        )

    async def _consume_queue(self) -> None:
        """Dequeue entries, dispatch to handler, and ACK on success."""
        if self._config.coalesce:
            from .subscriber_helpers.coalescing_consumer import consume_coalescing_stream_queue

            await consume_coalescing_stream_queue(
                self._queue,
                self._on_message,
                self._redis_client,
                self._config,
                self._subscriber_name,
                self._retry_counts,
                on_success=self.record_processed,
            )
        else:
            await consume_stream_queue(
                self._queue,
                self._on_message,
                self._redis_client,
                self._config,
                self._subscriber_name,
                self._retry_counts,
                on_success=self.record_processed,
            )


__all__ = ["MAX_STREAM_RETRIES", "MessageHandler", "RedisStreamSubscriber", "StreamConfig", "SubscriberHealthInfo"]
