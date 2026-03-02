"""Batch processing helpers for market update operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from common.constants.trading import MAX_PRICE_CENTS, MIN_PRICE_CENTS

from ..retry import with_redis_retry
from ..typing import ensure_awaitable

REJECTION_KEY_PREFIX = "algo_rejections"

from .ownership_helpers import algo_field

if TYPE_CHECKING:
    from redis.asyncio import Redis


@dataclass
class MarketSignal:
    """Internal representation of a market signal for batch processing."""

    ticker: str
    market_key: str
    t_bid: float | None
    t_ask: float | None
    algo: str


def build_market_signals(
    signals: Dict[str, Dict[str, Any]],
    algo: str,
    key_builder: Any,
) -> List[MarketSignal]:
    """Build MarketSignal objects from input signals dict."""
    result: List[MarketSignal] = []
    for ticker, data in signals.items():
        t_bid = data.get("t_bid")
        t_ask = data.get("t_ask")
        result.append(
            MarketSignal(
                ticker=ticker,
                market_key=key_builder(ticker),
                t_bid=t_bid,
                t_ask=t_ask,
                algo=algo,
            )
        )
    return result


def filter_valid_signals(
    market_signals: List[MarketSignal],
) -> Tuple[List[MarketSignal], List[str]]:
    """Filter out signals with no prices.

    Returns (valid_signals, failed_tickers).
    """
    valid: List[MarketSignal] = []
    failed: List[str] = []

    for sig in market_signals:
        if sig.t_bid is None and sig.t_ask is None:
            failed.append(sig.ticker)
            continue
        valid.append(sig)

    return valid, failed


def build_signal_mapping(
    sig: MarketSignal,
    algo: str,
) -> Dict[str, Any]:
    """Build the Redis hash mapping for a signal using namespaced fields.

    Writes {algo}:t_bid and {algo}:t_ask fields only.
    Tracker is responsible for setting algo/direction fields.
    """
    bid_field = algo_field(algo, "t_bid")
    ask_field = algo_field(algo, "t_ask")

    mapping: Dict[str, Any] = {}

    if sig.t_bid is not None:
        mapping[bid_field] = max(MIN_PRICE_CENTS, min(MAX_PRICE_CENTS, round(sig.t_bid)))
    if sig.t_ask is not None:
        mapping[ask_field] = max(MIN_PRICE_CENTS, min(MAX_PRICE_CENTS, round(sig.t_ask)))

    return mapping


def add_signal_to_pipeline(
    pipe: Any,
    sig: MarketSignal,
    mapping: Dict[str, Any],
) -> None:
    """Add a signal's updates to the Redis pipeline using namespaced fields."""
    pipe.hset(sig.market_key, mapping=mapping)

    # Delete stale opposite namespaced field when writing one-sided signal
    bid_field = algo_field(sig.algo, "t_bid")
    ask_field = algo_field(sig.algo, "t_ask")

    both_provided = sig.t_bid is not None and sig.t_ask is not None
    if not both_provided:
        if sig.t_bid is not None:
            pipe.hdel(sig.market_key, ask_field)
        elif sig.t_ask is not None:
            pipe.hdel(sig.market_key, bid_field)


async def get_rejection_stats(redis: "Redis", days: int = 1) -> Dict[str, Dict[str, int]]:
    """Get rejection statistics for the specified number of days."""
    today = date.today()
    day_strings = [(today - timedelta(days=i)).isoformat() for i in range(days)]
    keys = [f"{REJECTION_KEY_PREFIX}:{day_str}" for day_str in day_strings]

    async def _pipeline_fetch() -> list:
        pipe = redis.pipeline()
        for key in keys:
            pipe.hgetall(key)
        return await ensure_awaitable(pipe.execute())

    raw_results = await with_redis_retry(
        _pipeline_fetch,
        context="pipeline_rejection_stats",
    )

    stats: Dict[str, Dict[str, int]] = {}
    for day_str, data in zip(day_strings, raw_results):
        if data:
            stats[day_str] = {
                (f.decode("utf-8") if isinstance(f, bytes) else f): int(c.decode("utf-8") if isinstance(c, bytes) else c)
                for f, c in data.items()
            }

    return stats
