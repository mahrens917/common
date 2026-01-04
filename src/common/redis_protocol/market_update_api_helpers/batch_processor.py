"""Batch processing helpers for market update operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from ..typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

REJECTION_KEY_PREFIX = "algo_rejections"


@dataclass
class MarketSignal:
    """Internal representation of a market signal for batch processing."""

    ticker: str
    market_key: str
    t_yes_bid: float | None
    t_yes_ask: float | None
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
    """Filter signals by ownership, returning allowed signals and rejection/failure lists."""
    allowed: List[MarketSignal] = []
    rejected: List[str] = []
    failed: List[str] = []

    for sig in market_signals:
        if sig.t_yes_bid is None and sig.t_yes_ask is None:
            failed.append(sig.ticker)
            continue

        ownership = await check_ownership_func(redis, sig.market_key, algo, sig.ticker)
        if ownership.rejected:
            rejected.append(sig.ticker)
        else:
            allowed.append(sig)

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
    """Build the Redis hash mapping for a signal."""
    mapping: Dict[str, Any] = {"algo": algo, "direction": direction}
    if sig.t_yes_bid is not None:
        mapping["t_yes_bid"] = sig.t_yes_bid
    if sig.t_yes_ask is not None:
        mapping["t_yes_ask"] = sig.t_yes_ask
    return mapping


def add_signal_to_pipeline(
    pipe: Any,
    sig: MarketSignal,
    mapping: Dict[str, Any],
) -> None:
    """Add a signal's updates to the Redis pipeline."""
    pipe.hset(sig.market_key, mapping=mapping)

    both_provided = sig.t_yes_bid is not None and sig.t_yes_ask is not None
    if not both_provided:
        if sig.t_yes_bid is not None:
            pipe.hdel(sig.market_key, "t_yes_ask")
        elif sig.t_yes_ask is not None:
            pipe.hdel(sig.market_key, "t_yes_bid")


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
