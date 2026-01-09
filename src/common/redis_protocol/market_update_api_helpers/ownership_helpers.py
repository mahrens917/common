"""Ownership and stale market management helpers for market update operations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Callable, List, Optional, Set

from ..typing import ensure_awaitable
from .batch_processor import REJECTION_KEY_PREFIX

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OwnershipCheckResult:
    """Result of an ownership check."""

    success: bool
    rejected: bool
    reason: Optional[str]
    owning_algo: Optional[str]


async def check_ownership(
    redis: "Redis",
    market_key: str,
    requesting_algo: str,
    ticker: str,
) -> OwnershipCheckResult:
    """Check if the requesting algo can update this market."""
    current_algo = await ensure_awaitable(redis.hget(market_key, "algo"))

    if current_algo is not None:
        if isinstance(current_algo, bytes):
            current_algo = current_algo.decode("utf-8")

        if current_algo != requesting_algo:
            logger.debug(
                "Market %s owned by '%s', rejecting update from '%s'",
                ticker,
                current_algo,
                requesting_algo,
            )
            await record_rejection(redis, current_algo, requesting_algo)
            return OwnershipCheckResult(
                success=False,
                rejected=True,
                reason=f"owned_by_{current_algo}",
                owning_algo=current_algo,
            )

    return OwnershipCheckResult(success=True, rejected=False, reason=None, owning_algo=requesting_algo)


async def record_rejection(redis: "Redis", blocking_algo: str, requesting_algo: str) -> None:
    """Record a rejection event for tracking purposes."""
    today = date.today().isoformat()
    key = f"{REJECTION_KEY_PREFIX}:{today}"
    field = f"{blocking_algo}:{requesting_algo}"
    await ensure_awaitable(redis.hincrby(key, field, 1))


async def get_market_algo(redis: "Redis", market_key: str) -> Optional[str]:
    """Get the owning algo for a market."""
    algo = await ensure_awaitable(redis.hget(market_key, "algo"))
    if algo is None:
        return None
    if isinstance(algo, bytes):
        return algo.decode("utf-8")
    return str(algo)


async def scan_algo_owned_markets(
    redis: "Redis",
    scan_pattern: str,
    algo: str,
) -> Set[str]:
    """Find all market tickers where algo field equals the specified algo.

    Args:
        redis: Redis client
        scan_pattern: Pattern to scan (e.g., "markets:kalshi:*")
        algo: Algorithm name to match

    Returns:
        Set of tickers owned by this algo
    """
    owned_tickers: Set[str] = set()
    cursor = 0

    while True:
        cursor, keys = await ensure_awaitable(redis.scan(cursor, match=scan_pattern, count=1000))
        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            current_algo = await ensure_awaitable(redis.hget(key_str, "algo"))
            if current_algo is None:
                continue
            algo_str = current_algo.decode("utf-8") if isinstance(current_algo, bytes) else str(current_algo)
            if algo_str == algo:
                ticker = key_str.split(":")[-1]
                owned_tickers.add(ticker)
        if cursor == 0:
            break

    logger.debug("Found %d markets owned by %s", len(owned_tickers), algo)
    return owned_tickers


def algo_field(algo: str, field: str) -> str:
    """Build namespaced field name for algo-specific data."""
    return f"{algo}:{field}"


async def clear_stale_markets(
    redis: "Redis",
    stale_tickers: Set[str],
    algo: str,
    key_builder: Callable[[str], str],
) -> List[str]:
    """Clear stale markets owned by this algo.

    Removes {algo}:t_yes_bid, {algo}:t_yes_ask, algo, direction fields
    and publishes event updates.
    """
    cleared: List[str] = []
    bid_field = algo_field(algo, "t_yes_bid")
    ask_field = algo_field(algo, "t_yes_ask")

    for ticker in stale_tickers:
        market_key = key_builder(ticker)

        current_algo = await get_market_algo(redis, market_key)
        if current_algo != algo:
            logger.debug("Skipping clear for %s: owned by %s, not %s", ticker, current_algo, algo)
            continue

        await ensure_awaitable(redis.hdel(market_key, bid_field, ask_field, "algo", "direction"))
        cleared.append(ticker)

    if cleared:
        logger.info("Cleared %d stale markets for algo %s", len(cleared), algo)

    return cleared


async def clear_algo_ownership(redis: "Redis", market_key: str) -> bool:
    """Clear algo ownership from a market (used by --reset)."""
    result = await ensure_awaitable(redis.hdel(market_key, "algo"))
    return result > 0
