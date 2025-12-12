"""
Market Tracker - Check if markets are tracked in Redis

Handles existence checks for market data.
"""

import logging

from redis.asyncio import Redis

from ....error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


async def is_market_tracked(redis: Redis, market_key: str, market_ticker: str) -> bool:
    """
    Check if a market is tracked (check if market data exists)

    Args:
        redis: Redis connection
        market_key: Redis key for market
        market_ticker: Market ticker for logging

    Returns:
        True if market is tracked, False otherwise

    Raises:
        RuntimeError: If Redis operation fails
    """
    try:
        return await redis.exists(market_key)
    except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
        logger.error(
            "Error checking if market %s is tracked: %s",
            market_ticker,
            exc,
            exc_info=True,
        )
        raise
