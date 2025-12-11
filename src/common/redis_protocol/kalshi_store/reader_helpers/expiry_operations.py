"""
Expiry Operations - Market expiry and settlement checks

Handles expiry and settlement status checks.
"""

from redis.asyncio import Redis


async def check_expiry_status(redis: Redis, market_key: str, market_ticker: str, expiry_checker) -> bool:
    """
    Check if market is expired

    Args:
        redis: Redis connection
        market_key: Market key in Redis
        market_ticker: Market ticker string
        expiry_checker: ExpiryChecker instance

    Returns:
        True if market is expired
    """
    return await expiry_checker.is_market_expired(redis, market_key, market_ticker)


async def check_settlement_status(redis: Redis, market_key: str, market_ticker: str, expiry_checker) -> bool:
    """
    Check if market is settled

    Args:
        redis: Redis connection
        market_key: Market key in Redis
        market_ticker: Market ticker string
        expiry_checker: ExpiryChecker instance

    Returns:
        True if market is settled
    """
    return await expiry_checker.is_market_settled(redis, market_key, market_ticker)
