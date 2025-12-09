"""
Subscription Retriever - Get subscribed markets from Redis

Handles parsing subscription keys and extracting market tickers.
"""

import logging
from typing import Set

from redis.asyncio import Redis

from ....error_types import REDIS_ERRORS
from ....typing import ensure_awaitable

logger = logging.getLogger(__name__)

# Constants
_CONST_2 = 2


async def get_subscribed_markets(
    redis: Redis, subscriptions_key: str
) -> Set[str]:  # pragma: no cover - Redis coordination
    """
    Return the set of market tickers currently subscribed across all services.

    Args:
        redis: Redis connection
        subscriptions_key: Key for subscriptions hash

    Returns:
        Set of subscribed market tickers

    Raises:
        RuntimeError: If Redis connection fails
    """
    try:
        subscriptions = await ensure_awaitable(redis.hgetall(subscriptions_key))
        markets = set()
        for key, _value in subscriptions.items():
            key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            parts = key_str.split(":", 1)
            if len(parts) == _CONST_2:
                markets.add(parts[1])
    except REDIS_ERRORS as exc:
        logger.error("Error getting subscribed markets: %s", exc, exc_info=True)
        raise
    else:
        return markets
