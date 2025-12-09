"""Factory functions for creating specific types of distributed locks."""

from ..distributed_lock import DistributedLock


async def create_trade_lock(
    redis_client, ticker: str, timeout_seconds: int = 30
) -> DistributedLock:
    """
    Create a distributed lock for trading a specific market.

    Args:
        redis_client: Redis client instance
        ticker: Market ticker to lock
        timeout_seconds: Lock timeout in seconds

    Returns:
        DistributedLock instance for the market
    """
    lock_key = f"trade_lock:{ticker}"
    return DistributedLock(redis_client, lock_key, timeout_seconds)


async def create_liquidation_lock(
    redis_client, ticker: str, timeout_seconds: int = 60
) -> DistributedLock:
    """
    Create a distributed lock for liquidating positions in a specific market.

    Args:
        redis_client: Redis client instance
        ticker: Market ticker to lock
        timeout_seconds: Lock timeout in seconds (longer for liquidations)

    Returns:
        DistributedLock instance for the market liquidation
    """
    lock_key = f"liquidation_lock:{ticker}"
    return DistributedLock(redis_client, lock_key, timeout_seconds)
