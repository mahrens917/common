"""Stream publisher — wraps XADD with approximate trimming."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

from redis.typing import EncodableT, FieldT

from ..typing import ensure_awaitable
from .constants import STREAM_DEFAULT_MAXLEN

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


async def stream_publish(
    redis_client: "Redis",
    stream_name: str,
    fields: Dict[str, Any],
    *,
    maxlen: int = STREAM_DEFAULT_MAXLEN,
) -> str:
    """Publish a message to a Redis stream.

    All field values are converted to strings (Redis stream requirement).

    Args:
        redis_client: Async Redis client.
        stream_name: Target stream name.
        fields: Message fields (values will be str-coerced).
        maxlen: Approximate max stream length for trimming.

    Returns:
        The entry ID assigned by Redis.
    """
    str_fields: Dict[FieldT, EncodableT] = {k: str(v) for k, v in fields.items() if v is not None}

    entry_id: str = await ensure_awaitable(
        redis_client.xadd(stream_name, str_fields, maxlen=maxlen, approximate=True),
    )
    if isinstance(entry_id, bytes):
        entry_id = entry_id.decode("utf-8")
    logger.debug("Published to %s: %s", stream_name, entry_id)
    return entry_id


__all__ = ["stream_publish"]
