"""Coalescing queue consumer: deduplicates by identifier, processes only latest."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from ...retry import with_redis_retry
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


@dataclass
class _DispatchContext:
    """Shared context for winner dispatch functions."""

    on_message: MessageHandler
    redis_client: Any
    config: StreamConfig
    subscriber_name: str
    retry_counts: dict[str, int]
    queue: asyncio.Queue[_QueueEntry]
    timeout: float | None
    on_success: Callable[[], None] | None
    acked_ids: list[str] | None = None


async def _dispatch_single_winner(ctx: _DispatchContext, entry_id: str, identifier: str, fields: dict) -> None:
    """Dispatch a single coalesced winner to the handler."""
    try:
        payload = extract_payload(fields)
        if ctx.timeout is not None:
            await asyncio.wait_for(ctx.on_message(identifier, payload), timeout=ctx.timeout)
        else:
            await ctx.on_message(identifier, payload)
        # Collect entry_id for batched xack instead of individual xack per message
        if ctx.acked_ids is not None:
            ctx.acked_ids.append(entry_id)
        ctx.retry_counts.pop(entry_id, None)
        if ctx.on_success is not None:
            ctx.on_success()
    except asyncio.CancelledError:
        raise
    except Exception:  # policy_guard: allow-broad-except policy_guard: allow-silent-handler
        logger.exception("%s coalescing consumer error for entry %s", ctx.subscriber_name, entry_id)
        await handle_consumer_retry(
            entry_id,
            identifier,
            fields,
            ctx.queue,
            ctx.redis_client,
            ctx.config,
            ctx.retry_counts,
        )


async def _dispatch_winners(ctx: _DispatchContext, winners: Iterable[tuple[str, str, dict]]) -> None:
    """Dispatch all winners, concurrently if configured."""
    if ctx.config.max_concurrent_dispatches > 1:
        semaphore = asyncio.Semaphore(ctx.config.max_concurrent_dispatches)

        async def _bounded(eid: str, ident: str, flds: dict) -> None:
            async with semaphore:
                await _dispatch_single_winner(ctx, eid, ident, flds)

        await asyncio.gather(*[_bounded(eid, ident, flds) for eid, ident, flds in winners])
    else:
        for entry_id, identifier, fields in winners:
            await _dispatch_single_winner(ctx, entry_id, identifier, fields)


async def consume_coalescing_stream_queue(
    queue: asyncio.Queue[_QueueEntry],
    on_message: MessageHandler,
    redis_client: Any,
    config: StreamConfig,
    subscriber_name: str,
    retry_counts: dict[str, int],
    *,
    on_success: Callable[[], None] | None = None,
) -> None:
    """Dequeue entries, coalesce by identifier, and dispatch only the latest."""
    ctx = _DispatchContext(
        on_message=on_message,
        redis_client=redis_client,
        config=config,
        subscriber_name=subscriber_name,
        retry_counts=retry_counts,
        queue=queue,
        timeout=config.handler_timeout_s if config.handler_timeout_s > 0 else None,
        on_success=on_success,
    )

    while True:
        first = await queue.get()
        if first is None:
            queue.task_done()
            break

        rest = drain_queue(queue)
        all_entries: list[_QueueEntry] = [first] + rest
        winners, superseded_ids, saw_sentinel = coalesce_entries(all_entries)

        # Collect successful handler entry_ids for batched xack
        ctx.acked_ids = []
        await _dispatch_winners(ctx, winners)

        # Single batched xack for superseded + successfully processed entries
        all_ack_ids = superseded_ids + ctx.acked_ids
        if all_ack_ids:
            await with_redis_retry(
                lambda: redis_client.xack(config.stream_name, config.group_name, *all_ack_ids),
                context="xack-batch",
            )
        ctx.acked_ids = None

        # task_done for the first item (rest were task_done'd in drain_queue)
        queue.task_done()

        if saw_sentinel:
            break


__all__ = ["coalesce_entries", "consume_coalescing_stream_queue", "drain_queue"]
