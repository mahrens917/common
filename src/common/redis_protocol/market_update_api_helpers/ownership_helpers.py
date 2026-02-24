"""Stale market management helpers for market update operations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, List, Set

from ..retry import with_redis_retry
from ..typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


async def scan_algo_active_markets(
    redis: "Redis",
    scan_pattern: str,
    algo: str,
) -> Set[str]:
    """Find all market tickers where the algo has active theoretical prices.

    Checks for {algo}:t_bid or {algo}:t_ask fields via hmget.

    Args:
        redis: Redis client
        scan_pattern: Pattern to scan (e.g., "markets:kalshi:*")
        algo: Algorithm name to match

    Returns:
        Set of tickers with active prices for this algo
    """
    active_tickers: Set[str] = set()
    cursor = 0
    bid_field = f"{algo}:t_bid"
    ask_field = f"{algo}:t_ask"

    while True:
        cursor, keys = await with_redis_retry(
            lambda c=cursor: ensure_awaitable(redis.scan(c, match=scan_pattern, count=1000)),
            context=f"scan:{scan_pattern}",
        )
        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            values = await with_redis_retry(
                lambda k=key_str: ensure_awaitable(redis.hmget(k, [bid_field, ask_field])),
                context=f"hmget_theo:{key_str}",
            )
            if values[0] is not None or values[1] is not None:
                ticker = key_str.split(":")[-1]
                active_tickers.add(ticker)
        if cursor == 0:
            break

    logger.debug("Found %d markets with active prices for %s", len(active_tickers), algo)
    return active_tickers


def algo_field(algo: str, field: str) -> str:
    """Build namespaced field name for algo-specific data."""
    return f"{algo}:{field}"


async def clear_stale_markets(
    redis: "Redis",
    stale_tickers: Set[str],
    algo: str,
    key_builder: Callable[[str], str],
    metadata_fields: frozenset[str] = frozenset(),
) -> List[str]:
    """Clear stale markets for this algo.

    Removes {algo}:t_bid, {algo}:t_ask, {algo}:direction, {algo}:status,
    {algo}:reason fields, plus any algo-namespaced metadata fields.
    """
    cleared: List[str] = []
    base_fields = [
        algo_field(algo, "t_bid"),
        algo_field(algo, "t_ask"),
        algo_field(algo, "direction"),
        algo_field(algo, "status"),
        algo_field(algo, "reason"),
    ]
    extra_fields = [algo_field(algo, f) for f in sorted(metadata_fields)]
    all_fields = base_fields + extra_fields

    for ticker in stale_tickers:
        market_key = key_builder(ticker)

        await with_redis_retry(
            lambda mk=market_key: ensure_awaitable(redis.hdel(mk, *all_fields)),
            context=f"hdel_stale:{ticker}",
        )
        cleared.append(ticker)

    if cleared:
        logger.info("Cleared %d stale markets for algo %s", len(cleared), algo)

    return cleared
