"""Batch processing helpers for market update operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

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
    t_yes_bid: float | None
    t_yes_ask: float | None
    algo: str
    is_owner: bool = True  # Whether this algo owns (or will own) the market


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
            t_yes_bid=data.get("t_yes_bid"),
            t_yes_ask=data.get("t_yes_ask"),
            algo=algo,
        )
        for ticker, data in signals.items()
    ]


async def filter_allowed_signals(
    redis: "Redis",
    market_signals: List[MarketSignal],
    algo: str,
    check_ownership_func: Any,
) -> Tuple[List[MarketSignal], List[str], List[str]]:
    """Check ownership for signals and mark is_owner flag.

    In the new model, all writes are allowed (no rejection).
    The is_owner flag determines if algo/direction fields are set.
    """
    allowed: List[MarketSignal] = []
    rejected: List[str] = []  # No longer used, kept for API compatibility
    failed: List[str] = []

    for sig in market_signals:
        if sig.t_yes_bid is None and sig.t_yes_ask is None:
            failed.append(sig.ticker)
            continue

        # Check ownership but don't reject - just mark is_owner
        ownership = await check_ownership_func(redis, sig.market_key, algo, sig.ticker)
        # Create new signal with is_owner flag set
        updated_sig = MarketSignal(
            ticker=sig.ticker,
            market_key=sig.market_key,
            t_yes_bid=sig.t_yes_bid,
            t_yes_ask=sig.t_yes_ask,
            algo=sig.algo,
            is_owner=not ownership.rejected,
        )
        allowed.append(updated_sig)

    return allowed, rejected, failed


async def fetch_kalshi_prices(
    redis: "Redis",
    signals: List[MarketSignal],
) -> List[Any]:
    """Fetch current Kalshi prices for all signals using pipeline."""
    price_pipe = redis.pipeline()
    for sig in signals:
        price_pipe.hmget(sig.market_key, ["yes_bid", "yes_ask"])
    return await ensure_awaitable(price_pipe.execute())


def build_signal_mapping(
    sig: MarketSignal,
    direction: str,
    algo: str,
) -> Dict[str, Any]:
    """Build the Redis hash mapping for a signal using namespaced fields.

    Namespaced fields ({algo}:t_yes_bid, {algo}:t_yes_ask) are always written.
    Ownership fields (algo, direction) are only set if sig.is_owner is True.
    """
    bid_field = algo_field(algo, "t_yes_bid")
    ask_field = algo_field(algo, "t_yes_ask")

    mapping: Dict[str, Any] = {}

    # Always write namespaced theoretical prices
    if sig.t_yes_bid is not None:
        mapping[bid_field] = sig.t_yes_bid
    if sig.t_yes_ask is not None:
        mapping[ask_field] = sig.t_yes_ask

    # Only set ownership fields if this algo is the owner
    if sig.is_owner:
        mapping["algo"] = algo
        mapping["direction"] = direction

    return mapping


def add_signal_to_pipeline(
    pipe: Any,
    sig: MarketSignal,
    mapping: Dict[str, Any],
) -> None:
    """Add a signal's updates to the Redis pipeline using namespaced fields."""
    pipe.hset(sig.market_key, mapping=mapping)

    # Delete stale opposite namespaced field when writing one-sided signal
    bid_field = algo_field(sig.algo, "t_yes_bid")
    ask_field = algo_field(sig.algo, "t_yes_ask")

    both_provided = sig.t_yes_bid is not None and sig.t_yes_ask is not None
    if not both_provided:
        if sig.t_yes_bid is not None:
            pipe.hdel(sig.market_key, ask_field)
        elif sig.t_yes_ask is not None:
            pipe.hdel(sig.market_key, bid_field)


async def get_rejection_stats(redis: "Redis", days: int = 1) -> Dict[str, Dict[str, int]]:
    """Get rejection statistics for the specified number of days."""
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
