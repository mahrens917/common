"""Theoretical price writing helpers for market update operations."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Optional

from common.constants import VALID_ALGO_NAMES

from ..retry import with_redis_retry
from ..streams import algo_event_stream, stream_publish
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
    one_shot: bool = False


def _clamp_price(value: float) -> int:
    """Round and clamp a theoretical price to valid Kalshi range [1, 99]."""
    return max(1, min(99, round(value)))


def parse_int(value: object) -> int:
    """Parse value to int, treating None/empty as 0."""
    if value is None or value in {"", b""}:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return int(round(float(value)))
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


def validate_algo_name(algo: str) -> None:
    """Validate that algo name is in the canonical set. Raises ValueError if invalid."""
    if algo not in VALID_ALGO_NAMES:
        raise ValueError(f"Unknown algo '{algo}'. Valid algos: {sorted(VALID_ALGO_NAMES)}")


_CachedPrices = tuple[int | None, int | None]
_price_cache: dict[tuple[str, str], _CachedPrices] = {}


def _prices_unchanged(
    market_key: str,
    algo: str,
    t_bid: int | None,
    t_ask: int | None,
) -> bool:
    """Check if clamped prices match the in-memory cache of last-written values."""
    cache_key = (market_key, algo)
    return _price_cache.get(cache_key) == (t_bid, t_ask)


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
    Prices are clamped to valid Kalshi range [1, 99] before writing.
    Skips write and publish when clamped values match last-written values.
    """
    validate_algo_name(algo)
    t_bid = _clamp_price(prices.t_bid) if prices.t_bid is not None else None
    t_ask = _clamp_price(prices.t_ask) if prices.t_ask is not None else None

    if _prices_unchanged(market_key, algo, t_bid, t_ask):
        return

    mapping = build_price_mapping(algo, t_bid, t_ask)

    await with_redis_retry(
        lambda: ensure_awaitable(redis.hset(market_key, mapping=mapping)),
        context=f"hset_prices:{ticker}",
    )
    await delete_stale_opposite_field(redis, market_key, algo, t_bid, t_ask)

    logger.debug(
        "Updated market %s: %s:t_bid=%s, %s:t_ask=%s",
        ticker,
        algo,
        t_bid,
        algo,
        t_ask,
    )

    _price_cache[(market_key, algo)] = (t_bid, t_ask)

    clamped_prices = PriceSignal(t_bid=t_bid, t_ask=t_ask, one_shot=prices.one_shot)
    await publish_market_event_update(redis, market_key, ticker, algo, clamped_prices)


def _add_price_fields(fields: dict[str, str], prices: PriceSignal) -> None:
    """Add non-None price fields from PriceSignal to the given dict."""
    if prices.t_ask is not None:
        fields["t_ask"] = str(prices.t_ask)
    if prices.t_bid is not None:
        fields["t_bid"] = str(prices.t_bid)


async def _publish_algo_event(
    redis: "Redis",
    ticker: str,
    algo: str,
    prices: PriceSignal,
    event_ticker: str,
) -> None:
    """Publish a single per-algo event carrying signal data and market event fields."""
    fields: dict[str, str] = {
        "market_ticker": ticker,
        "algorithm": algo,
        "event_ticker": event_ticker,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _add_price_fields(fields, prices)
    if prices.one_shot:
        fields["one_shot"] = "true"
    payload_dict: dict[str, object] = {
        "ticker": ticker,
        "market_ticker": ticker,
        "event_ticker": event_ticker,
        "t_ask": prices.t_ask,
        "t_bid": prices.t_bid,
        "algorithm": algo,
    }
    if prices.one_shot:
        payload_dict["one_shot"] = True
    fields["payload"] = json.dumps(payload_dict)
    await with_redis_retry(
        lambda: stream_publish(redis, algo_event_stream(algo), fields),
        context=f"stream_publish_algo_event:{ticker}",
    )
    logger.debug("Published algo event for %s (%s)", ticker, algo)


async def publish_market_event_update(
    redis: "Redis",
    market_key: str,
    ticker: str,
    algo: str = "",
    prices: PriceSignal = PriceSignal(),
) -> None:
    """Publish market event update to notify tracker of theoretical price change."""
    if not algo:
        return

    event_ticker_raw = await with_redis_retry(
        lambda: ensure_awaitable(redis.hget(market_key, "event_ticker")),
        context=f"hget_event_ticker:{ticker}",
    )
    event_ticker = ""
    if event_ticker_raw:
        event_ticker = event_ticker_raw.decode("utf-8") if isinstance(event_ticker_raw, bytes) else event_ticker_raw

    await _publish_algo_event(redis, ticker, algo, prices, event_ticker)
