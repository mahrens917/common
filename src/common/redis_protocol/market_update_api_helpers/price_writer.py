"""Theoretical price writing helpers for market update operations."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Optional

from ..retry import with_redis_retry
from ..streams import ALGO_SIGNAL_STREAM, MARKET_EVENT_STREAM, stream_publish
from ..typing import ensure_awaitable
from .ownership_helpers import algo_field

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceSignal:
    """Bundle of theoretical price data for a market update."""

    t_bid: Optional[float] = None
    t_ask: Optional[float] = None
    edge: Optional[float] = None
    signal: Optional[str] = None


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
    t_bid: int | None,
    t_ask: int | None,
    kalshi_bid: int,
    kalshi_ask: int,
) -> str:
    """Compute trading direction by comparing theoretical to Kalshi prices."""
    buy_edge = t_ask is not None and 0 < kalshi_ask < t_ask
    sell_edge = t_bid is not None and kalshi_bid > 0 and kalshi_bid > t_bid

    if buy_edge and sell_edge:
        return "NONE"
    if buy_edge:
        return "BUY"
    if sell_edge:
        return "SELL"
    return "NONE"


def build_price_mapping(
    algo: str,
    t_bid: Optional[float],
    t_ask: Optional[float],
) -> Dict[str, float | str]:
    """Build the namespaced price mapping."""
    bid_field = algo_field(algo, "t_bid")
    ask_field = algo_field(algo, "t_ask")

    mapping: Dict[str, float | str] = {}
    if t_bid is not None:
        mapping[bid_field] = t_bid
    if t_ask is not None:
        mapping[ask_field] = t_ask
    return mapping


async def delete_stale_opposite_field(
    redis: "Redis",
    market_key: str,
    algo: str,
    t_bid: Optional[float],
    t_ask: Optional[float],
) -> None:
    """Delete stale opposite namespaced field when writing one-sided signal."""
    bid_field = algo_field(algo, "t_bid")
    ask_field = algo_field(algo, "t_ask")

    both_provided = t_bid is not None and t_ask is not None
    if both_provided:
        return

    if t_bid is not None:
        await with_redis_retry(
            lambda: ensure_awaitable(redis.hdel(market_key, ask_field)),
            context="hdel_stale_ask",
        )
    elif t_ask is not None:
        await with_redis_retry(
            lambda: ensure_awaitable(redis.hdel(market_key, bid_field)),
            context="hdel_stale_bid",
        )


async def write_theoretical_prices(
    redis: "Redis",
    market_key: str,
    algo: str,
    prices: PriceSignal,
    ticker: str,
) -> None:
    """Write theoretical prices to Redis using namespaced fields.

    Algos write their own {algo}:t_bid and {algo}:t_ask fields.
    Tracker is responsible for setting algo/direction fields.
    """
    mapping = build_price_mapping(algo, prices.t_bid, prices.t_ask)

    await with_redis_retry(
        lambda: ensure_awaitable(redis.hset(market_key, mapping=mapping)),
        context=f"hset_prices:{ticker}",
    )
    await delete_stale_opposite_field(redis, market_key, algo, prices.t_bid, prices.t_ask)

    logger.debug(
        "Updated market %s: %s:t_bid=%s, %s:t_ask=%s",
        ticker,
        algo,
        prices.t_bid,
        algo,
        prices.t_ask,
    )

    await publish_market_event_update(redis, market_key, ticker, algo, prices)


async def publish_market_event_update(
    redis: "Redis",
    market_key: str,
    ticker: str,
    algo: str = "",
    prices: PriceSignal = PriceSignal(),
) -> None:
    """Publish market event update to notify tracker of theoretical price change."""
    event_ticker = await with_redis_retry(
        lambda: ensure_awaitable(redis.hget(market_key, "event_ticker")),
        context=f"hget_event_ticker:{ticker}",
    )
    if not event_ticker:
        logger.debug("No event_ticker for %s, skipping publish", ticker)
    else:
        if isinstance(event_ticker, bytes):
            event_ticker = event_ticker.decode("utf-8")

        await with_redis_retry(
            lambda: stream_publish(
                redis,
                MARKET_EVENT_STREAM,
                {
                    "event_ticker": event_ticker,
                    "market_ticker": ticker,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ),
            context=f"stream_publish_event:{ticker}",
        )
        logger.debug("Published market event update for %s to stream %s", ticker, MARKET_EVENT_STREAM)

    # Publish algo signal to stream for tracker's external provider cache
    if algo:
        algo_fields: dict[str, str] = {
            "ticker": ticker,
            "algorithm": algo,
        }
        if prices.t_ask is not None:
            algo_fields["t_ask"] = str(prices.t_ask)
        if prices.t_bid is not None:
            algo_fields["t_bid"] = str(prices.t_bid)
        if prices.edge is not None:
            algo_fields["edge"] = str(prices.edge)
        if prices.signal is not None:
            algo_fields["signal"] = prices.signal
        algo_fields["payload"] = json.dumps(
            {
                "ticker": ticker,
                "t_ask": prices.t_ask,
                "t_bid": prices.t_bid,
                "algorithm": algo,
                "edge": prices.edge,
                "signal": prices.signal,
            }
        )
        await with_redis_retry(
            lambda: stream_publish(redis, ALGO_SIGNAL_STREAM, algo_fields),
            context=f"stream_publish_algo:{ticker}",
        )
        logger.debug("Published algo signal for %s (%s)", ticker, algo)
