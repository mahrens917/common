"""Event publisher for market orderbook updates.

Publishes market event updates to a Redis Stream whenever
orderbook snapshots or deltas are written.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ...streams.constants import MARKET_EVENT_STREAM
from ...streams.publisher import stream_publish
from ...typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


async def publish_market_event(
    redis: "Redis",
    market_key: str,
    market_ticker: str,
    timestamp: str,
) -> bool:
    """
    Publish market event update to the stream.

    Args:
        redis: Redis client
        market_key: Redis key for the market
        market_ticker: Market ticker string
        timestamp: Update timestamp

    Returns:
        True if published, False if no event_ticker found
    """
    try:
        event_ticker = await ensure_awaitable(redis.hget(market_key, "event_ticker"))
        if not event_ticker:
            logger.debug("No event_ticker for %s, skipping publish", market_ticker)
            return False

        if isinstance(event_ticker, bytes):
            event_ticker = event_ticker.decode("utf-8")

        await stream_publish(
            redis,
            MARKET_EVENT_STREAM,
            {"event_ticker": event_ticker, "market_ticker": market_ticker, "timestamp": timestamp},
        )
        logger.debug("Published market event update for %s to stream %s", market_ticker, MARKET_EVENT_STREAM)
    except (RuntimeError, ConnectionError, OSError) as exc:
        logger.debug("Failed to publish market event update for %s: %s", market_ticker, exc)
        raise

    return True


__all__ = ["publish_market_event"]
