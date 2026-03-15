"""Pending entry recovery and consumer group initialization."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, List, Tuple

from common.redis_protocol.streams.constants import PENDING_CLAIM_IDLE_MS
from common.redis_protocol.streams.consumer_group import claim_pending_entries as _claim_pending_entries
from common.redis_protocol.streams.consumer_group import (
    ensure_consumer_group,
)

if TYPE_CHECKING:
    from ..subscriber import StreamConfig

logger = logging.getLogger(__name__)

_MISSING_IDENTIFIER = ""
_UNKNOWN_AGE_MS = 0


async def initialize_consumer_group(
    redis_client: Any,
    stream: str,
    group: str,
) -> None:
    """Initialize a consumer group, creating the stream if needed.

    Safe to call on every startup -- BUSYGROUP is silently handled.
    """
    await ensure_consumer_group(redis_client, stream, group)
    logger.info("Consumer group %s ready on stream %s", group, stream)


async def recover_pending_entries(
    redis_client: Any,
    stream: str,
    group: str,
    consumer: str,
    idle_ms: int = PENDING_CLAIM_IDLE_MS,
) -> List[Tuple[str, dict]]:
    """Claim and return entries that were pending from a previous consumer.

    These are entries that were delivered but never ACK'd (e.g., due to crash).
    """
    entries = await _claim_pending_entries(redis_client, stream, group, consumer, idle_ms)
    if entries:
        logger.info(
            "Recovered %d pending entries from %s (group=%s, consumer=%s)",
            len(entries),
            stream,
            group,
            consumer,
        )
    return entries


def parse_entry_timestamp_ms(entry_id: str) -> int:
    """Parse the timestamp in milliseconds from a stream entry ID.

    Stream entry IDs have the format ``{timestamp_ms}-{seq}``.
    Returns 0 if the ID cannot be parsed.
    """
    dash_pos = entry_id.find("-")
    if dash_pos <= 0:
        return 0
    try:
        return int(entry_id[:dash_pos])
    except ValueError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        return 0


def _compute_entry_age(entry_id: str, now_ms: float) -> tuple[int, float]:
    """Compute entry timestamp and age in ms. Returns (entry_ts_ms, age_ms)."""
    entry_ts_ms = parse_entry_timestamp_ms(entry_id)
    age_ms = now_ms - entry_ts_ms if entry_ts_ms > 0 else _UNKNOWN_AGE_MS
    return entry_ts_ms, age_ms


async def recover_and_filter_pending(
    pending: list,
    redis_client: Any,
    config: StreamConfig,
    queue: asyncio.Queue,
    subscriber_name: str,
) -> None:
    """Recover pending entries by re-enqueuing for processing."""
    now_ms = time.time() * 1000
    old_count = 0

    for entry_id, fields in pending:
        entry_ts_ms, age_ms = _compute_entry_age(entry_id, now_ms)

        if entry_ts_ms == 0 or age_ms > PENDING_CLAIM_IDLE_MS:
            old_count += 1
            logger.warning("%s recovering old pending entry %s (age_ms=%d)", subscriber_name, entry_id, age_ms)
        identifier = fields.get(config.identifier_field, _MISSING_IDENTIFIER)
        try:
            queue.put_nowait((entry_id, identifier, fields))
        except asyncio.QueueFull:  # policy_guard: allow-silent-handler
            logger.warning("%s pending recovery queue full, entry %s will be retried on next restart", subscriber_name, entry_id)
            break

    if old_count:
        logger.warning("%s recovered %d old pending entries for processing", subscriber_name, old_count)


def _decode_entry_id(raw_id: Any) -> str:
    """Decode a bytes entry ID to string."""
    return raw_id.decode("utf-8") if isinstance(raw_id, bytes) else raw_id


def _collect_all_ids(entries: list) -> list[str]:
    """Collect decoded IDs from all claimed entries."""
    return [_decode_entry_id(entry_id) for entry_id, _fields in entries]


async def purge_stale_pending(
    redis_client: Any,
    stream: str,
    group: str,
    consumer: str,
    max_age_ms: int,
) -> int:
    """Bulk-ACK all pending entries via XAUTOCLAIM pagination.

    Claims entries idle longer than max_age_ms and ACKs them unconditionally.
    Returns the number of purged entries.
    """
    from ...retry import with_redis_retry
    from ...typing import ensure_awaitable
    from ..constants import XAUTOCLAIM_MIN_RESULT_LENGTH

    purged = 0
    cursor = "0-0"

    while True:
        result = await ensure_awaitable(
            redis_client.xautoclaim(stream, group, consumer, min_idle_time=max_age_ms, start_id=cursor),
        )
        if not result or len(result) < XAUTOCLAIM_MIN_RESULT_LENGTH:
            break

        next_cursor, entries = result[0], result[1]
        entry_ids = _collect_all_ids(entries)

        if entry_ids:
            await with_redis_retry(
                lambda: redis_client.xack(stream, group, *entry_ids),
                context="xack-purge-stale",
            )
            purged += len(entry_ids)

        next_cursor_str = _decode_entry_id(next_cursor)
        if next_cursor_str == "0-0" or not entries:
            break
        cursor = next_cursor_str

    return purged


_XPENDING_BATCH_SIZE = 1000


async def discard_all_pending(
    redis_client: Any,
    stream: str,
    group: str,
    consumer: str,
) -> int:
    """ACK all pending entries without processing them.

    Uses XPENDING to read entry IDs from the PEL, then bulk-ACKs them.
    Handles ghost entries (trimmed from stream but still in PEL) that
    XAUTOCLAIM silently skips.
    """
    from ...retry import with_redis_retry

    discarded = 0
    start_id = "-"

    while True:
        pending = await redis_client.xpending_range(
            stream,
            group,
            min=start_id,
            max="+",
            count=_XPENDING_BATCH_SIZE,
        )
        if not pending:
            break

        entry_ids = [_decode_entry_id(entry["message_id"]) for entry in pending]

        await with_redis_retry(
            lambda ids=entry_ids: redis_client.xack(stream, group, *ids),
            context="xack-discard-pending",
        )
        discarded += len(entry_ids)

        if len(pending) < _XPENDING_BATCH_SIZE:
            break
        last_id = entry_ids[-1]
        parts = last_id.split("-")
        start_id = f"{parts[0]}-{int(parts[1]) + 1}"

    if discarded:
        logger.info("Discarded %d pending entries from %s (group=%s)", discarded, stream, group)
    return discarded


__all__ = [
    "discard_all_pending",
    "initialize_consumer_group",
    "parse_entry_timestamp_ms",
    "purge_stale_pending",
    "recover_and_filter_pending",
    "recover_pending_entries",
]
