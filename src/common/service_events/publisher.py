"""Publish structured service events to the service_events Redis stream."""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any, Dict

from common.redis_protocol.streams.constants import SERVICE_EVENTS_STREAM
from common.redis_protocol.streams.publisher import stream_publish

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


async def publish_service_event(
    redis_client: "Redis",
    service: str,
    event_type: str,
    severity: str,
    message: str,
    details: Dict[str, Any] | None = None,
) -> str:
    """Publish a structured event to stream:service_events via XADD.

    Args:
        redis_client: Async Redis client.
        service: Name of the originating service (e.g. "tracker", "kalshi").
        event_type: Event category (e.g. "trade_executed", "ws_disconnect").
        severity: Alert severity string ("info", "warning", "critical").
        message: Human-readable event description.
        details: Optional dict of structured metadata (JSON-serialized).

    Returns:
        The stream entry ID assigned by Redis.
    """
    fields: Dict[str, Any] = {
        "service": service,
        "event_type": event_type,
        "severity": severity,
        "message": message,
        "timestamp": str(time.time()),
    }
    if details is not None:
        fields["details"] = json.dumps(details)

    entry_id = await stream_publish(redis_client, SERVICE_EVENTS_STREAM, fields)
    logger.debug("Published service event: %s/%s -> %s", service, event_type, entry_id)
    return entry_id
