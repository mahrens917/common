"""Queue consumer: payload extraction, handler dispatch, retry handling."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:
    from ..subscriber import StreamConfig

from ...retry import with_redis_retry

logger = logging.getLogger(__name__)

MessageHandler = Callable[[str, dict], Awaitable[None]]

MAX_STREAM_RETRIES = 3
_MAX_RETRY_TRACKING_ENTRIES = 1000


def is_json_object_string(raw: object) -> bool:
    """Check if a value looks like a parseable JSON object string."""
    if not isinstance(raw, (str, bytes, bytearray)):
        return False
    text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
    stripped = text.strip()
    return stripped.startswith("{") and stripped.endswith("}")


def extract_payload(fields: dict) -> dict:
    """Extract payload from stream entry fields.

    If the entry has a 'payload' field containing valid JSON, parse it.
    Otherwise return the fields dict directly.
    """
    raw_payload = fields.get("payload")
    if raw_payload is None or not is_json_object_string(raw_payload):
        return fields
    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError:  # policy_guard: allow-silent-handler
        logger.warning("Malformed JSON payload, using raw fields: %.100s", raw_payload)
        return fields
    if isinstance(parsed, dict):
        return parsed
    return fields


async def handle_consumer_retry(
    entry_id: str,
    identifier: str,
    fields: dict,
    queue: asyncio.Queue,
    redis_client: Any,
    config: StreamConfig,
    retry_counts: dict[str, int],
) -> None:
    """Handle retry logic for a failed stream entry."""
    prior = retry_counts.get(entry_id)
    if prior is None:
        prior = 0
    retries = prior + 1
    if retries < MAX_STREAM_RETRIES:
        # Safety cap: if retry_counts grows too large, evict oldest entries
        if len(retry_counts) >= _MAX_RETRY_TRACKING_ENTRIES:
            _evict_oldest = next(iter(retry_counts))
            retry_counts.pop(_evict_oldest, None)
            logger.warning("Retry tracking overflow, evicted entry %s", _evict_oldest)
        retry_counts[entry_id] = retries
        await queue.put((entry_id, identifier, fields))
        logger.warning("Retrying message %s (attempt %d)", entry_id, retries)
    else:
        await redis_client.xack(config.stream_name, config.group_name, entry_id)
        retry_counts.pop(entry_id, None)
        logger.critical("Permanently dropping message %s after %d retries", entry_id, MAX_STREAM_RETRIES)


async def consume_stream_queue(
    queue: asyncio.Queue,
    on_message: MessageHandler,
    redis_client: Any,
    config: StreamConfig,
    subscriber_name: str,
    retry_counts: dict[str, int],
) -> None:
    """Dequeue entries, dispatch to handler, and ACK on success."""
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
        entry_id = None
        try:
            entry_id, identifier, fields = item
            payload = extract_payload(fields)
            await on_message(identifier, payload)
            await with_redis_retry(
                lambda: redis_client.xack(config.stream_name, config.group_name, entry_id),
                context=f"xack-{entry_id}",
            )
            retry_counts.pop(entry_id, None)
        except asyncio.CancelledError:
            raise
        except Exception:  # policy_guard: allow-broad-except policy_guard: allow-silent-handler
            logger.exception("%s consumer error for entry %s", subscriber_name, entry_id)
            if entry_id is not None:
                await handle_consumer_retry(entry_id, identifier, fields, queue, redis_client, config, retry_counts)
        finally:
            queue.task_done()


__all__ = ["MAX_STREAM_RETRIES", "consume_stream_queue", "extract_payload", "is_json_object_string"]
