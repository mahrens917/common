"""Consumer group management — idempotent creation and pending entry recovery."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List, Tuple

from ..retry import with_redis_retry
from ..typing import ensure_awaitable
from .constants import PENDING_CLAIM_IDLE_MS, XAUTOCLAIM_MIN_RESULT_LENGTH

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


async def ensure_consumer_group(
    redis_client: "Redis",
    stream: str,
    group: str,
    start_id: str = "0",
) -> None:
    """Create a consumer group idempotently.

    Uses MKSTREAM to create the stream if it doesn't exist.
    Catches BUSYGROUP to make this safe to call on every startup.
    """
    try:
        await with_redis_retry(
            lambda: ensure_awaitable(redis_client.xgroup_create(stream, group, id=start_id, mkstream=True)),
            context=f"xgroup_create:{stream}/{group}",
        )
        logger.info("Created consumer group %s on stream %s", group, stream)
    except Exception as exc:  # policy_guard: allow-broad-except
        if "BUSYGROUP" in str(exc):
            logger.debug("Consumer group %s already exists on %s", group, stream)
        else:
            raise


async def claim_pending_entries(
    redis_client: "Redis",
    stream: str,
    group: str,
    consumer: str,
    idle_ms: int = PENDING_CLAIM_IDLE_MS,
) -> List[Tuple[str, dict]]:
    """Claim pending entries that have been idle for too long.

    Uses XAUTOCLAIM to take ownership of entries that a previous consumer
    abandoned (e.g., after a crash). Returns list of (entry_id, fields) tuples.
    """
    result: Any = await with_redis_retry(
        lambda: ensure_awaitable(redis_client.xautoclaim(stream, group, consumer, min_idle_time=idle_ms, start_id="0-0")),
        context=f"xautoclaim:{stream}/{group}",
    )
    # XAUTOCLAIM returns (next_start_id, [(id, fields), ...], deleted_ids)
    if not result or len(result) < XAUTOCLAIM_MIN_RESULT_LENGTH:
        return []

    entries = result[1]
    claimed: List[Tuple[str, dict]] = []
    for entry_id, fields in entries:
        decoded_id = entry_id.decode("utf-8") if isinstance(entry_id, bytes) else entry_id
        decoded_fields = _decode_fields(fields)
        claimed.append((decoded_id, decoded_fields))

    if claimed:
        logger.info("Claimed %d pending entries from %s/%s", len(claimed), stream, group)
    return claimed


def _decode_fields(fields: Any) -> dict:
    """Decode bytes keys/values to strings."""
    if isinstance(fields, dict):
        return {
            (k.decode("utf-8") if isinstance(k, bytes) else k): (v.decode("utf-8") if isinstance(v, bytes) else v)
            for k, v in fields.items()
        }
    return {}


__all__ = ["claim_pending_entries", "ensure_consumer_group"]
