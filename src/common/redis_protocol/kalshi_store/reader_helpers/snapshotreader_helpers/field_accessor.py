"""
Field Accessor - Get specific market fields from Redis

Handles individual field retrieval with error handling.
"""

import logging

from redis.asyncio import Redis

from ....error_types import REDIS_ERRORS
from ....typing import ensure_awaitable

logger = logging.getLogger(__name__)


async def get_market_field(redis: Redis, market_key: str, ticker: str, field: str) -> str:
    """
    Get specific market field

    Args:
        redis: Redis connection
        market_key: Redis key for market
        ticker: Market ticker for logging
        field: Field name to retrieve

    Returns:
        Field value as string, empty string if not found
    """
    try:
        result = await ensure_awaitable(redis.hget(market_key, field))
        if result:
            return result

        else:
            return ""
    except REDIS_ERRORS as exc:
        logger.error("Redis error getting field %s for %s: %s", field, ticker, exc, exc_info=True)
        return ""
