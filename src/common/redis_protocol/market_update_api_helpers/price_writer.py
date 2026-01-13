"""Theoretical price writing helpers for market update operations."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Optional

from ..retry import with_redis_retry
from ..typing import ensure_awaitable
from .ownership_helpers import algo_field, get_market_algo

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


def parse_int(value: object) -> int:
    """Parse value to int, treating None/empty as 0."""
    if value is None or value in {"", b""}:
        return 0
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return int(float(value))
    raise TypeError(f"Cannot parse {type(value).__name__} to int")


def compute_direction(
    t_yes_bid: int | None,
    t_yes_ask: int | None,
    kalshi_bid: int,
    kalshi_ask: int,
) -> str:
    """Compute trading direction by comparing theoretical to Kalshi prices."""
    buy_edge = t_yes_ask is not None and 0 < kalshi_ask < t_yes_ask
    sell_edge = t_yes_bid is not None and kalshi_bid > 0 and kalshi_bid > t_yes_bid

    if buy_edge and sell_edge:
        return "NONE"
    if buy_edge:
        return "BUY"
    if sell_edge:
        return "SELL"
    return "NONE"


def build_price_mapping(
    algo: str,
    t_yes_bid: Optional[float],
    t_yes_ask: Optional[float],
) -> Dict[str, float | str]:
    """Build the namespaced price mapping."""
    bid_field = algo_field(algo, "t_yes_bid")
    ask_field = algo_field(algo, "t_yes_ask")

    mapping: Dict[str, float | str] = {}
    if t_yes_bid is not None:
        mapping[bid_field] = t_yes_bid
    if t_yes_ask is not None:
        mapping[ask_field] = t_yes_ask
    return mapping


async def add_ownership_fields(
    redis: "Redis",
    market_key: str,
    mapping: Dict[str, float | str],
    algo: str,
    t_yes_bid: Optional[float],
    t_yes_ask: Optional[float],
) -> bool:
    """Add ownership fields (algo, direction) to mapping if this algo is owner.

    Returns True if this algo is the owner.
    """
    current_algo = await get_market_algo(redis, market_key)
    is_owner = current_algo is None or current_algo == algo

    if is_owner:
        kalshi_data = await with_redis_retry(
            lambda: ensure_awaitable(redis.hmget(market_key, ["yes_bid", "yes_ask"])),
            context="hmget_kalshi_prices",
        )
        kalshi_bid = parse_int(kalshi_data[0])
        kalshi_ask = parse_int(kalshi_data[1])

        t_bid_int = int(t_yes_bid) if t_yes_bid is not None else None
        t_ask_int = int(t_yes_ask) if t_yes_ask is not None else None
        direction = compute_direction(t_bid_int, t_ask_int, kalshi_bid, kalshi_ask)

        mapping["algo"] = algo
        mapping["direction"] = direction

    return is_owner


async def delete_stale_opposite_field(
    redis: "Redis",
    market_key: str,
    algo: str,
    t_yes_bid: Optional[float],
    t_yes_ask: Optional[float],
) -> None:
    """Delete stale opposite namespaced field when writing one-sided signal."""
    bid_field = algo_field(algo, "t_yes_bid")
    ask_field = algo_field(algo, "t_yes_ask")

    both_provided = t_yes_bid is not None and t_yes_ask is not None
    if both_provided:
        return

    if t_yes_bid is not None:
        await with_redis_retry(
            lambda: ensure_awaitable(redis.hdel(market_key, ask_field)),
            context="hdel_stale_ask",
        )
    elif t_yes_ask is not None:
        await with_redis_retry(
            lambda: ensure_awaitable(redis.hdel(market_key, bid_field)),
            context="hdel_stale_bid",
        )


async def write_theoretical_prices(
    redis: "Redis",
    market_key: str,
    algo: str,
    t_yes_bid: Optional[float],
    t_yes_ask: Optional[float],
    ticker: str,
) -> None:
    """Write theoretical prices to Redis using namespaced fields.

    All algos can write their own {algo}:t_yes_* fields.
    Only the owner (or first writer) sets algo/direction fields.
    """
    mapping = build_price_mapping(algo, t_yes_bid, t_yes_ask)
    is_owner = await add_ownership_fields(redis, market_key, mapping, algo, t_yes_bid, t_yes_ask)

    await with_redis_retry(
        lambda: ensure_awaitable(redis.hset(market_key, mapping=mapping)),
        context=f"hset_prices:{ticker}",
    )
    await delete_stale_opposite_field(redis, market_key, algo, t_yes_bid, t_yes_ask)

    logger.debug(
        "Updated market %s: algo=%s, %s:t_yes_bid=%s, %s:t_yes_ask=%s, owner=%s",
        ticker,
        algo,
        algo,
        t_yes_bid,
        algo,
        t_yes_ask,
        is_owner,
    )

    await publish_market_event_update(redis, market_key, ticker)


async def publish_market_event_update(
    redis: "Redis",
    market_key: str,
    ticker: str,
) -> None:
    """Publish market event update to notify tracker of theoretical price change."""
    try:
        event_ticker = await with_redis_retry(
            lambda: ensure_awaitable(redis.hget(market_key, "event_ticker")),
            context=f"hget_event_ticker:{ticker}",
        )
        if not event_ticker:
            logger.debug("No event_ticker for %s, skipping publish", ticker)
            return

        if isinstance(event_ticker, bytes):
            event_ticker = event_ticker.decode("utf-8")

        channel = f"market_event_updates:{event_ticker}"
        payload = json.dumps(
            {
                "market_ticker": ticker,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        await with_redis_retry(
            lambda: ensure_awaitable(redis.publish(channel, payload)),
            context=f"publish_event:{ticker}",
        )
        logger.debug("Published market event update for %s to %s", ticker, channel)
    except (RuntimeError, ConnectionError, OSError) as exc:
        logger.debug("Failed to publish market event update for %s: %s", ticker, exc)
        raise
