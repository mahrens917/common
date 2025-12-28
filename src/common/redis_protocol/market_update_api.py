"""
Market Update API

Provides algo-aware market update functionality with ownership checking.
All algos (weather, pdf, peak, extreme) use this API to update theoretical prices.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Dict, Optional

from .typing import RedisClient, ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

VALID_ALGOS = frozenset({"weather", "pdf", "peak", "extreme"})
REJECTION_KEY_PREFIX = "algo_rejections"


@dataclass(frozen=True)
class MarketUpdateResult:
    """Result of a market update request."""

    success: bool
    rejected: bool
    reason: Optional[str]
    owning_algo: Optional[str]


async def request_market_update(
    redis: "Redis",
    market_key: str,
    algo: str,
    t_yes_bid: Optional[float],
    t_yes_ask: Optional[float],
    ticker: Optional[str] = None,
) -> MarketUpdateResult:
    """
    Request to update theoretical prices for a market.

    Enforces algo ownership - first algo to touch a market owns it.
    Subsequent updates from the same algo are allowed.
    Updates from different algos are rejected with a warning.

    Args:
        redis: Redis client
        market_key: Redis key for the market (e.g., markets:kalshi:weather:KXHIGH-KDCA-202501)
        algo: Algorithm name (weather, pdf, peak, extreme)
        t_yes_bid: Theoretical bid price (can be None to skip)
        t_yes_ask: Theoretical ask price (can be None to skip)
        ticker: Optional ticker for logging (extracted from key if not provided)

    Returns:
        MarketUpdateResult with success/rejected status and reason
    """
    if algo not in VALID_ALGOS:
        raise ValueError(f"Invalid algo '{algo}'. Must be one of: {sorted(VALID_ALGOS)}")

    if t_yes_bid is None and t_yes_ask is None:
        return MarketUpdateResult(success=False, rejected=False, reason="no_prices_provided", owning_algo=None)

    display_ticker = ticker if ticker else market_key.split(":")[-1]

    ownership_result = await _check_ownership(redis, market_key, algo, display_ticker)
    if ownership_result.rejected:
        return ownership_result

    await _write_theoretical_prices(redis, market_key, algo, t_yes_bid, t_yes_ask, display_ticker)

    return MarketUpdateResult(success=True, rejected=False, reason=None, owning_algo=algo)


async def _check_ownership(
    redis: "Redis",
    market_key: str,
    requesting_algo: str,
    ticker: str,
) -> MarketUpdateResult:
    """Check if the requesting algo can update this market."""
    current_algo = await ensure_awaitable(redis.hget(market_key, "algo"))

    if current_algo is not None:
        if isinstance(current_algo, bytes):
            current_algo = current_algo.decode("utf-8")

        if current_algo != requesting_algo:
            logger.warning(
                "Market %s owned by '%s', rejecting update from '%s'",
                ticker,
                current_algo,
                requesting_algo,
            )
            await _record_rejection(redis, current_algo, requesting_algo)
            return MarketUpdateResult(
                success=False,
                rejected=True,
                reason=f"owned_by_{current_algo}",
                owning_algo=current_algo,
            )

    return MarketUpdateResult(success=True, rejected=False, reason=None, owning_algo=requesting_algo)


async def _write_theoretical_prices(
    redis: "Redis",
    market_key: str,
    algo: str,
    t_yes_bid: Optional[float],
    t_yes_ask: Optional[float],
    ticker: str,
) -> None:
    """Write theoretical prices and algo ownership to Redis."""
    mapping: dict[str, str | float] = {"algo": algo}

    if t_yes_bid is not None:
        mapping["t_yes_bid"] = t_yes_bid
    if t_yes_ask is not None:
        mapping["t_yes_ask"] = t_yes_ask

    await ensure_awaitable(redis.hset(market_key, mapping=mapping))

    logger.debug(
        "Updated market %s: algo=%s, t_yes_bid=%s, t_yes_ask=%s",
        ticker,
        algo,
        t_yes_bid,
        t_yes_ask,
    )


async def _record_rejection(redis: "Redis", blocking_algo: str, requesting_algo: str) -> None:
    """Record a rejection event for tracking purposes."""
    today = date.today().isoformat()
    key = f"{REJECTION_KEY_PREFIX}:{today}"
    field = f"{blocking_algo}:{requesting_algo}"
    await ensure_awaitable(redis.hincrby(key, field, 1))


async def get_rejection_stats(redis: "Redis", days: int = 1) -> Dict[str, Dict[str, int]]:
    """
    Get rejection statistics for the specified number of days.

    Args:
        redis: Redis client
        days: Number of days to include (1 = today only)

    Returns:
        Dict mapping date strings to dicts of {blocking:requesting -> count}
    """
    from datetime import timedelta

    stats: Dict[str, Dict[str, int]] = {}
    today = date.today()

    for i in range(days):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        key = f"{REJECTION_KEY_PREFIX}:{day_str}"

        data = await ensure_awaitable(redis.hgetall(key))
        if data:
            day_stats: Dict[str, int] = {}
            for field, count in data.items():
                if isinstance(field, bytes):
                    field = field.decode("utf-8")
                if isinstance(count, bytes):
                    count = int(count.decode("utf-8"))
                day_stats[field] = int(count)
            stats[day_str] = day_stats

    return stats


async def clear_algo_ownership(redis: "Redis", market_key: str) -> bool:
    """
    Clear algo ownership from a market (used by --reset).

    Args:
        redis: Redis client
        market_key: Redis key for the market

    Returns:
        True if field was cleared, False if it didn't exist
    """
    result = await ensure_awaitable(redis.hdel(market_key, "algo"))
    return result > 0


async def get_market_algo(redis: "Redis", market_key: str) -> Optional[str]:
    """
    Get the owning algo for a market.

    Args:
        redis: Redis client
        market_key: Redis key for the market

    Returns:
        Algo name or None if no algo owns this market
    """
    algo = await ensure_awaitable(redis.hget(market_key, "algo"))
    if algo is None:
        return None
    if isinstance(algo, bytes):
        return algo.decode("utf-8")
    return str(algo)


__all__ = [
    "request_market_update",
    "clear_algo_ownership",
    "get_market_algo",
    "get_rejection_stats",
    "MarketUpdateResult",
    "VALID_ALGOS",
]
