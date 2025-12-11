"""
Market Operations - High-level market query operations

Provides orchestration for complex market queries.
"""

import logging
from typing import Dict, List, Optional, Set

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


async def get_subscribed_markets_safe(redis: Redis, subscriptions_key: str, snapshot_reader) -> Set[str]:
    """
    Get subscribed markets with error handling

    Args:
        redis: Redis connection
        subscriptions_key: Key for subscriptions set
        snapshot_reader: SnapshotReader instance

    Returns:
        Set of market tickers
    """
    return await snapshot_reader.get_subscribed_markets(redis, subscriptions_key)


async def check_market_tracked(redis: Redis, market_key: str, market_ticker: str, snapshot_reader) -> bool:
    """
    Check if market is tracked

    Args:
        redis: Redis connection
        market_key: Market key in Redis
        market_ticker: Market ticker string
        snapshot_reader: SnapshotReader instance

    Returns:
        True if market is tracked
    """
    return await snapshot_reader.is_market_tracked(redis, market_key, market_ticker)


async def query_market_for_strike_expiry(
    redis: Redis,
    currency: str,
    expiry: str,
    strike: float,
    markets: Set[str],
    get_market_key_func,
    market_lookup,
) -> Optional[Dict]:
    """
    Query market data for specific strike/expiry with error handling

    Args:
        redis: Redis connection
        currency: Currency symbol
        expiry: Expiry date string
        strike: Strike price
        markets: Set of market tickers
        get_market_key_func: Function to get market key
        market_lookup: MarketLookup instance

    Returns:
        Market data or None
    """
    try:
        return await market_lookup.get_market_data_for_strike_expiry(redis, currency, expiry, strike, markets, get_market_key_func)
    except REDIS_ERRORS as exc:
        logger.error(
            "Redis error getting market data for %s %s @ %s: %s",
            currency,
            expiry,
            strike,
            exc,
            exc_info=True,
        )
        return None


async def aggregate_strike_data(
    markets: List[Dict], market_aggregator, logger_instance: logging.Logger, currency: str
) -> Dict[str, List[Dict]]:
    """
    Aggregate markets into strike/expiry summary

    Args:
        markets: List of market records
        market_aggregator: MarketAggregator instance
        logger_instance: Logger instance
        currency: Currency symbol

    Returns:
        Dictionary mapping expiry to list of strike info
    """
    grouped, market_by_ticker = market_aggregator.aggregate_markets_by_point(markets)
    summary = market_aggregator.build_strike_summary(grouped, market_by_ticker)
    total_points = len(grouped)
    multi_market_points = sum(1 for tickers in grouped.values() if len(tickers) > 1)
    if total_points:
        logger_instance.debug(
            "Prepared %s strike points for %s (multi-market=%s)",
            total_points,
            currency,
            multi_market_points,
        )
    return summary
