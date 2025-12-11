"""
Snapshot Operations - Market snapshot retrieval

Handles fetching complete market snapshots and metadata.
"""

from typing import Any, Dict

from redis.asyncio import Redis


async def fetch_market_snapshot(
    redis: Redis, market_key: str, ticker: str, snapshot_reader, *, include_orderbook: bool = True
) -> Dict[str, Any]:
    """
    Fetch complete market snapshot

    Args:
        redis: Redis connection
        market_key: Market key in Redis
        ticker: Market ticker string
        snapshot_reader: SnapshotReader instance
        include_orderbook: Whether to include orderbook data

    Returns:
        Market snapshot dictionary
    """
    return await snapshot_reader.get_market_snapshot(redis, market_key, ticker, include_orderbook=include_orderbook)


async def fetch_market_metadata(redis: Redis, market_key: str, ticker: str, snapshot_reader) -> Dict:
    """
    Fetch market metadata only

    Args:
        redis: Redis connection
        market_key: Market key in Redis
        ticker: Market ticker string
        snapshot_reader: SnapshotReader instance

    Returns:
        Market metadata dictionary
    """
    return await snapshot_reader.get_market_metadata(redis, market_key, ticker)


async def fetch_market_field(redis: Redis, market_key: str, ticker: str, field: str, snapshot_reader) -> str:
    """
    Fetch specific market field

    Args:
        redis: Redis connection
        market_key: Market key in Redis
        ticker: Market ticker string
        field: Field name to retrieve
        snapshot_reader: SnapshotReader instance

    Returns:
        Field value as string
    """
    return await snapshot_reader.get_market_field(redis, market_key, ticker, field)
