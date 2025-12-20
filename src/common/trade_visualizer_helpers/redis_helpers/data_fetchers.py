"""Data fetching operations via Redis for trade visualizer."""

from datetime import datetime
from typing import TYPE_CHECKING, List

from .connection import get_redis_connection

if TYPE_CHECKING:
    from ..liquidity_fetcher import MarketState
    from ..redis_fetcher import RedisFetcher


async def get_executed_trades_for_station(
    redis_fetcher: "RedisFetcher",
    station_icao: str,
    start_time: datetime,
    end_time: datetime,
):
    """Fetch executed trades using the local Redis helper for tests."""
    redis = await get_redis_connection()
    try:
        return await redis_fetcher.get_executed_trades_for_station(redis, station_icao, start_time, end_time)
    finally:
        await redis.aclose()


async def get_market_liquidity_states(
    redis_fetcher: "RedisFetcher",
    station_icao: str,
    start_time: datetime,
    end_time: datetime,
) -> List["MarketState"]:
    """Fetch liquidity states using the Redis helper for tests."""
    redis = await get_redis_connection()
    try:
        return await redis_fetcher.get_market_liquidity_states(redis, station_icao, start_time, end_time)
    finally:
        await redis.aclose()
