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


async def recover_and_filter_pending(
    pending: list,
    redis_client: Any,
    config: StreamConfig,
    queue: asyncio.Queue,
    subscriber_name: str,
) -> None:
    """Recover all pending entries by enqueuing them for processing."""
    now_ms = time.time() * 1000
    old_count = 0
    for entry_id, fields in pending:
        entry_ts_ms = parse_entry_timestamp_ms(entry_id)
        age_ms = now_ms - entry_ts_ms
        if entry_ts_ms <= 0:
            age_ms = 0
        if entry_ts_ms == 0 or age_ms > PENDING_CLAIM_IDLE_MS:
            old_count += 1
            logger.warning(
                "%s recovering old pending entry %s (age_ms=%d)",
                subscriber_name,
                entry_id,
                age_ms,
            )
        identifier = fields.get(config.identifier_field, _MISSING_IDENTIFIER)
        try:
            queue.put_nowait((entry_id, identifier, fields))
        except asyncio.QueueFull:  # policy_guard: allow-silent-handler
            logger.warning(
                "%s pending recovery queue full, entry %s will be retried on next restart",
                subscriber_name,
                entry_id,
            )
            break
    if old_count:
        logger.warning("%s recovered %d old pending entries for processing", subscriber_name, old_count)


__all__ = [
    "initialize_consumer_group",
    "parse_entry_timestamp_ms",
    "recover_and_filter_pending",
    "recover_pending_entries",
]
