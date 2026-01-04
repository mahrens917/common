"""
Market Update API

Provides algo-aware market update functionality with ownership checking.
All algos (weather, pdf, peak, extreme) use this API to update theoretical prices.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .typing import RedisClient, ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

VALID_ALGOS = frozenset({"weather", "pdf", "peak", "extreme"})


def compute_direction(
    t_yes_bid: int | None,
    t_yes_ask: int | None,
    kalshi_bid: int,
    kalshi_ask: int,
) -> str:
    """Compute trading direction by comparing theoretical to Kalshi prices.

    Args:
        t_yes_bid: Theoretical YES bid (for SELL signals), None if not set
        t_yes_ask: Theoretical YES ask (for BUY signals), None if not set
        kalshi_bid: Current Kalshi YES bid price
        kalshi_ask: Current Kalshi YES ask price

    Returns:
        "BUY" if kalshi_ask < t_yes_ask (undervalued)
        "SELL" if kalshi_bid > t_yes_bid (overvalued)
        "NONE" if both conditions true (conflict) or neither true
    """
    buy_edge = t_yes_ask is not None and 0 < kalshi_ask < t_yes_ask
    sell_edge = t_yes_bid is not None and kalshi_bid > 0 and kalshi_bid > t_yes_bid

    if buy_edge and sell_edge:
        return "NONE"
    if buy_edge:
        return "BUY"
    if sell_edge:
        return "SELL"
    return "NONE"


from .market_update_api_helpers.batch_processor import REJECTION_KEY_PREFIX, get_rejection_stats


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
            logger.debug(
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


def _parse_int(value: object) -> int:
    """Parse value to int, treating None/empty as 0."""
    if value is None or value in {"", b""}:
        return 0
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return int(float(value))
    raise TypeError(f"Cannot parse {type(value).__name__} to int")


async def _write_theoretical_prices(
    redis: "Redis",
    market_key: str,
    algo: str,
    t_yes_bid: Optional[float],
    t_yes_ask: Optional[float],
    ticker: str,
) -> None:
    """Write theoretical prices, direction, and algo ownership to Redis."""
    # Read current Kalshi prices to compute direction
    kalshi_data = await ensure_awaitable(redis.hmget(market_key, ["yes_bid", "yes_ask"]))
    kalshi_bid = _parse_int(kalshi_data[0])
    kalshi_ask = _parse_int(kalshi_data[1])

    # Compute direction from theoretical vs Kalshi prices
    t_bid_int = int(t_yes_bid) if t_yes_bid is not None else None
    t_ask_int = int(t_yes_ask) if t_yes_ask is not None else None
    direction = compute_direction(t_bid_int, t_ask_int, kalshi_bid, kalshi_ask)

    mapping: dict[str, str | float] = {"algo": algo, "direction": direction}

    # Build mapping with provided prices
    if t_yes_bid is not None:
        mapping["t_yes_bid"] = t_yes_bid
    if t_yes_ask is not None:
        mapping["t_yes_ask"] = t_yes_ask

    await ensure_awaitable(redis.hset(market_key, mapping=mapping))

    # Delete stale opposite field only when writing a one-sided signal
    # (signal flipped from BUY to SELL or vice versa)
    # If both sides provided, keep both (e.g., PDF provides full probabilities)
    both_provided = t_yes_bid is not None and t_yes_ask is not None
    if not both_provided:
        if t_yes_bid is not None:
            await ensure_awaitable(redis.hdel(market_key, "t_yes_ask"))
        elif t_yes_ask is not None:
            await ensure_awaitable(redis.hdel(market_key, "t_yes_bid"))

    logger.debug(
        "Updated market %s: algo=%s, t_yes_bid=%s, t_yes_ask=%s, direction=%s",
        ticker,
        algo,
        t_yes_bid,
        t_yes_ask,
        direction,
    )

    await _publish_market_event_update(redis, market_key, ticker)


async def _publish_market_event_update(
    redis: "Redis",
    market_key: str,
    ticker: str,
) -> None:
    """Publish market event update to notify tracker of theoretical price change."""
    try:
        event_ticker = await ensure_awaitable(redis.hget(market_key, "event_ticker"))
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
        await ensure_awaitable(redis.publish(channel, payload))
        logger.debug("Published market event update for %s to %s", ticker, channel)
    except (RuntimeError, ConnectionError, OSError) as exc:
        logger.debug("Failed to publish market event update for %s: %s", ticker, exc)
        raise


async def _record_rejection(redis: "Redis", blocking_algo: str, requesting_algo: str) -> None:
    """Record a rejection event for tracking purposes."""
    today = date.today().isoformat()
    key = f"{REJECTION_KEY_PREFIX}:{today}"
    field = f"{blocking_algo}:{requesting_algo}"
    await ensure_awaitable(redis.hincrby(key, field, 1))


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


@dataclass(frozen=True)
class BatchUpdateResult:
    """Result of a batch market update."""

    succeeded: List[str]
    rejected: List[str]
    failed: List[str]


async def batch_update_market_signals(
    redis: "Redis",
    signals: Dict[str, Dict[str, Any]],
    algo: str,
    key_builder: Any,
) -> BatchUpdateResult:
    """Atomically update theoretical prices for multiple markets using Redis transactions."""
    from .market_update_api_helpers import (
        add_signal_to_pipeline,
        build_market_signals,
        build_signal_mapping,
        fetch_kalshi_prices,
        filter_allowed_signals,
    )

    if algo not in VALID_ALGOS:
        raise ValueError(f"Invalid algo '{algo}'. Must be one of: {sorted(VALID_ALGOS)}")

    if not signals:
        return BatchUpdateResult(succeeded=[], rejected=[], failed=[])

    market_signals = build_market_signals(signals, algo, key_builder)
    allowed, rejected, failed = await filter_allowed_signals(redis, market_signals, algo, _check_ownership)

    if not allowed:
        return BatchUpdateResult(succeeded=[], rejected=rejected, failed=failed)

    sorted_signals = sorted(allowed, key=lambda s: (s.t_yes_ask is not None, s.ticker))
    price_results = await fetch_kalshi_prices(redis, sorted_signals)
    pipe = redis.pipeline(transaction=True)

    for sig, prices in zip(sorted_signals, price_results):
        direction = _compute_direction_from_prices(sig, prices)
        mapping = build_signal_mapping(sig, direction, algo)
        add_signal_to_pipeline(pipe, sig, mapping)

    return await _execute_batch_transaction(redis, pipe, sorted_signals, rejected, failed, algo)


def _compute_direction_from_prices(sig: Any, prices: List[Any]) -> str:
    """Compute direction from signal and Kalshi prices."""
    kalshi_bid = _parse_int(prices[0])
    kalshi_ask = _parse_int(prices[1])
    t_bid_int = int(sig.t_yes_bid) if sig.t_yes_bid is not None else None
    t_ask_int = int(sig.t_yes_ask) if sig.t_yes_ask is not None else None
    return compute_direction(t_bid_int, t_ask_int, kalshi_bid, kalshi_ask)


async def _execute_batch_transaction(
    redis: "Redis",
    pipe: Any,
    sorted_signals: List[Any],
    rejected: List[str],
    failed: List[str],
    algo: str,
) -> BatchUpdateResult:
    """Execute the batch transaction and publish event updates."""
    succeeded: List[str] = []
    try:
        await ensure_awaitable(pipe.execute())
        succeeded = [sig.ticker for sig in sorted_signals]
        logger.debug("Batch updated %d markets atomically for algo %s", len(succeeded), algo)
    except (RuntimeError, ConnectionError, OSError):
        logger.exception("Failed to execute batch update for algo %s", algo)
        failed.extend(sig.ticker for sig in sorted_signals)
        raise

    for sig in sorted_signals:
        try:
            await _publish_market_event_update(redis, sig.market_key, sig.ticker)
        except (RuntimeError, ConnectionError, OSError):  # Expected, non-critical  # policy_guard: allow-silent-handler
            pass

    return BatchUpdateResult(succeeded=succeeded, rejected=rejected, failed=failed)


__all__ = [
    "batch_update_market_signals",
    "BatchUpdateResult",
    "clear_algo_ownership",
    "compute_direction",
    "get_market_algo",
    "get_rejection_stats",
    "MarketUpdateResult",
    "request_market_update",
    "VALID_ALGOS",
]
