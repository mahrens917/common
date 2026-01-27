"""Batch processing helpers for market update operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

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
    return [
        MarketSignal(
            ticker=ticker,
            market_key=key_builder(ticker),
            t_bid=data.get("t_bid"),
            t_ask=data.get("t_ask"),
            algo=algo,
        )
        for ticker, data in signals.items()
    ]


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
        mapping[bid_field] = sig.t_bid
    if sig.t_ask is not None:
        mapping[ask_field] = sig.t_ask

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
    stats: Dict[str, Dict[str, int]] = {}
    today = date.today()

    for i in range(days):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        key = f"{REJECTION_KEY_PREFIX}:{day_str}"

        data = await with_redis_retry(
            lambda k=key: ensure_awaitable(redis.hgetall(k)),
            context=f"hgetall_rejection_stats:{day_str}",
        )
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
