"""
Throttled event publisher for market orderbook updates.

Publishes market event updates to Redis pubsub with per-event throttling
to reduce downstream processing load from high-frequency orderbook changes.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Dict

from ...typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Throttle window in seconds - only publish once per event within this window
_THROTTLE_WINDOW_SECONDS = 0.25  # 250ms

# Track last publish time per event_ticker
_last_publish_time: Dict[str, float] = {}


def clear_publisher_state() -> None:
    """Clear publisher state. Call on startup or for testing."""
    _last_publish_time.clear()


async def publish_market_event_throttled(
    redis: "Redis",
    market_key: str,
    market_ticker: str,
    timestamp: str,
) -> bool:
    """
    Publish market event update with per-event throttling.

    Only publishes if at least _THROTTLE_WINDOW_SECONDS has passed since
    the last publish for this event. Reduces downstream processing load
    when orderbooks update rapidly.

    Args:
        redis: Redis client
        market_key: Redis key for the market
        market_ticker: Market ticker string
        timestamp: Update timestamp

    Returns:
        True if published, False if throttled
    """
    try:
        event_ticker = await ensure_awaitable(redis.hget(market_key, "event_ticker"))
        if not event_ticker:
            logger.debug("No event_ticker for %s, skipping publish", market_ticker)
            return False

        if isinstance(event_ticker, bytes):
            event_ticker = event_ticker.decode("utf-8")

        now = time.monotonic()
        last_publish = 0.0
        if event_ticker in _last_publish_time:
            last_publish = _last_publish_time[event_ticker]

        if (now - last_publish) < _THROTTLE_WINDOW_SECONDS:
            logger.debug(
                "Throttled publish for event %s (market %s), %.1fms since last",
                event_ticker,
                market_ticker,
                (now - last_publish) * 1000,
            )
            return False

        _last_publish_time[event_ticker] = now

        channel = f"market_event_updates:{event_ticker}"
        payload = json.dumps({"market_ticker": market_ticker, "timestamp": timestamp})
        await redis.publish(channel, payload)
        logger.debug("Published market event update for %s to %s", market_ticker, channel)
    except (RuntimeError, ConnectionError, OSError) as exc:
        logger.debug("Failed to publish market event update for %s: %s", market_ticker, exc)
        raise

    return True


__all__ = ["clear_publisher_state", "publish_market_event_throttled"]
