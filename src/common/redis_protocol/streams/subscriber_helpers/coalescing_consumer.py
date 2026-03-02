"""Coalescing queue consumer: deduplicates by identifier, processes only latest."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from .consumer import extract_payload, handle_consumer_retry

if TYPE_CHECKING:
    from ..subscriber import StreamConfig

logger = logging.getLogger(__name__)

MessageHandler = Callable[[str, dict], Awaitable[None]]

# Type alias for a queue entry: (entry_id, identifier, fields) or None sentinel
_QueueEntry = tuple[str, str, dict] | None


def drain_queue(queue: asyncio.Queue[_QueueEntry]) -> list[_QueueEntry]:
    """Pull all immediately available items from the queue without blocking.

    Calls ``task_done()`` for each item drained.
    """
    items: list[_QueueEntry] = []
    while not queue.empty():
        item = queue.get_nowait()
        items.append(item)
        queue.task_done()
    return items


def coalesce_entries(
    entries: list[_QueueEntry],
) -> tuple[Iterable[tuple[str, str, dict]], list[str], bool]:
    """Deduplicate entries by identifier, keeping only the latest per identifier.

    Returns:
        winners: iterable of (entry_id, identifier, fields) to process.
        superseded_ids: entry_ids that were superseded (to be bulk-ACKed).
        saw_sentinel: whether a None stop sentinel was found.
    """
    latest: dict[str, tuple[str, str, dict]] = {}
    superseded_ids: list[str] = []
    saw_sentinel = False

    for entry in entries:
        if entry is None:
            saw_sentinel = True
            continue
        entry_id, identifier, fields = entry
        previous = latest.get(identifier)
        if previous is not None:
            superseded_ids.append(previous[0])
        latest[identifier] = (entry_id, identifier, fields)

    return latest.values(), superseded_ids, saw_sentinel


async def consume_coalescing_stream_queue(
    queue: asyncio.Queue[_QueueEntry],
    on_message: MessageHandler,
    redis_client: Any,
    config: StreamConfig,
    subscriber_name: str,
    retry_counts: dict[str, int],
) -> None:
    """Dequeue entries, coalesce by identifier, and dispatch only the latest."""
    while True:
        first = await queue.get()
        if first is None:
            queue.task_done()
            break

        rest = drain_queue(queue)
        all_entries: list[_QueueEntry] = [first] + rest
        winners, superseded_ids, saw_sentinel = coalesce_entries(all_entries)

        if superseded_ids:
            await redis_client.xack(config.stream_name, config.group_name, *superseded_ids)

        for entry_id, identifier, fields in winners:
            try:
                payload = extract_payload(fields)
                await on_message(identifier, payload)
                await redis_client.xack(config.stream_name, config.group_name, entry_id)
                retry_counts.pop(entry_id, None)
            except asyncio.CancelledError:
                raise
            except Exception:  # policy_guard: allow-broad-except policy_guard: allow-silent-handler
                logger.exception("%s coalescing consumer error for entry %s", subscriber_name, entry_id)
                await handle_consumer_retry(entry_id, identifier, fields, queue, redis_client, config, retry_counts)

        # task_done for the first item (rest were task_done'd in drain_queue)
        queue.task_done()

        if saw_sentinel:
            break


__all__ = ["coalesce_entries", "consume_coalescing_stream_queue", "drain_queue"]
