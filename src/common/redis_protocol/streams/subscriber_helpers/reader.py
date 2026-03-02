"""Stream reading: XREADGROUP wrapper and read loop."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, List, Tuple

from common.redis_protocol.streams.message_decoder import decode_stream_response

if TYPE_CHECKING:
    from ..subscriber import StreamConfig

logger = logging.getLogger(__name__)

_DEFAULT_BATCH_SIZE = 100
_DEFAULT_BLOCK_MS = 5000
_MISSING_IDENTIFIER = ""


async def read_stream_entries(
    redis_client: Any,
    stream: str,
    group: str,
    consumer: str,
    *,
    count: int = _DEFAULT_BATCH_SIZE,
    block_ms: int = _DEFAULT_BLOCK_MS,
) -> List[Tuple[str, dict]]:
    """Read new entries from a stream using XREADGROUP.

    Reads entries assigned to this consumer that haven't been ACK'd yet
    (using ">" as the start ID to get only new entries).
    """
    result: Any = await redis_client.xreadgroup(group, consumer, {stream: ">"}, count=count, block=block_ms)
    return decode_stream_response(result)


async def stream_read_loop(
    is_running: Callable[[], bool],
    redis_client: Any,
    config: StreamConfig,
    queue: asyncio.Queue,
    subscriber_name: str,
) -> None:
    """Read entries from the stream and enqueue for processing."""
    while is_running():
        try:
            entries = await read_stream_entries(
                redis_client,
                config.stream_name,
                config.group_name,
                config.consumer_name,
                count=config.batch_size,
                block_ms=config.block_ms,
            )
            for entry_id, fields in entries:
                identifier = fields.get(config.identifier_field, _MISSING_IDENTIFIER)
                await queue.put((entry_id, identifier, fields))
            if not entries:
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # policy_guard: allow-broad-except policy_guard: allow-silent-handler
            logger.warning("%s read error, retrying: %s", subscriber_name, exc)
            await asyncio.sleep(1)


__all__ = ["read_stream_entries", "stream_read_loop"]
