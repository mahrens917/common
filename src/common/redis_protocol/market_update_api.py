"""
Market Update API

Provides algo-aware market update functionality with ownership checking.
All algos (whale, peak, edge, pdf, weather) use this API to update theoretical prices.

Field naming convention:
  - {algo}:t_yes_bid, {algo}:t_yes_ask - namespaced theoretical prices per algo
  - algo - which algo owns this market (first to write claims ownership)
  - direction - computed from owner's theoretical prices vs Kalshi prices
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set

from .typing import RedisClient, ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

VALID_ALGOS = frozenset({"whale", "peak", "edge", "pdf", "weather"})


def algo_field(algo: str, field: str) -> str:
    """Build namespaced field name for algo-specific data.

    Args:
        algo: Algorithm name (e.g., "pdf", "weather")
        field: Field name (e.g., "t_yes_bid", "t_yes_ask")

    Returns:
        Namespaced field like "pdf:t_yes_bid"
    """
    return f"{algo}:{field}"


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
    Update theoretical prices for a market using namespaced fields.

    All algos can write their {algo}:t_yes_* fields to any market.
    First algo to write claims ownership (algo field).
    Only the owner's theoretical prices are used for direction computation.

    Args:
        redis: Redis client
        market_key: Redis key for the market (e.g., markets:kalshi:weather:KXHIGH-KDCA-202501)
        algo: Algorithm name (whale, peak, edge, pdf, weather)
        t_yes_bid: Theoretical bid price (can be None to skip)
        t_yes_ask: Theoretical ask price (can be None to skip)
        ticker: Optional ticker for logging (extracted from key if not provided)

    Returns:
        MarketUpdateResult with success status and owning algo
    """
    if algo not in VALID_ALGOS:
        raise ValueError(f"Invalid algo '{algo}'. Must be one of: {sorted(VALID_ALGOS)}")

    if t_yes_bid is None and t_yes_ask is None:
        return MarketUpdateResult(success=False, rejected=False, reason="no_prices_provided", owning_algo=None)

    display_ticker = ticker if ticker else market_key.split(":")[-1]

    await _write_theoretical_prices(redis, market_key, algo, t_yes_bid, t_yes_ask, display_ticker)

    # Get current owner (may be this algo if we just claimed, or another algo)
    current_owner = await get_market_algo(redis, market_key)

    return MarketUpdateResult(success=True, rejected=False, reason=None, owning_algo=current_owner)


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
    """Write theoretical prices to Redis using namespaced fields.

    All algos can write their own {algo}:t_yes_* fields.
    Only the owner (or first writer) sets algo/direction fields.
    """
    # Build namespaced field names
    bid_field = algo_field(algo, "t_yes_bid")
    ask_field = algo_field(algo, "t_yes_ask")

    # Always write this algo's namespaced theoretical prices
    mapping: dict[str, str | float] = {}
    if t_yes_bid is not None:
        mapping[bid_field] = t_yes_bid
    if t_yes_ask is not None:
        mapping[ask_field] = t_yes_ask

    # Check current ownership
    current_algo = await get_market_algo(redis, market_key)
    is_owner = current_algo is None or current_algo == algo

    if is_owner:
        # Claim or maintain ownership, compute direction
        kalshi_data = await ensure_awaitable(redis.hmget(market_key, ["yes_bid", "yes_ask"]))
        kalshi_bid = _parse_int(kalshi_data[0])
        kalshi_ask = _parse_int(kalshi_data[1])

        t_bid_int = int(t_yes_bid) if t_yes_bid is not None else None
        t_ask_int = int(t_yes_ask) if t_yes_ask is not None else None
        direction = compute_direction(t_bid_int, t_ask_int, kalshi_bid, kalshi_ask)

        mapping["algo"] = algo
        mapping["direction"] = direction

    await ensure_awaitable(redis.hset(market_key, mapping=mapping))

    # Delete stale opposite field only when writing a one-sided signal
    both_provided = t_yes_bid is not None and t_yes_ask is not None
    if not both_provided:
        if t_yes_bid is not None:
            await ensure_awaitable(redis.hdel(market_key, ask_field))
        elif t_yes_ask is not None:
            await ensure_awaitable(redis.hdel(market_key, bid_field))

    logger.debug(
        "Updated market %s: algo=%s, %s=%s, %s=%s, owner=%s",
        ticker,
        algo,
        bid_field,
        t_yes_bid,
        ask_field,
        t_yes_ask,
        is_owner,
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


@dataclass(frozen=True)
class AlgoUpdateResult:
    """Result of update_and_clear_stale operation."""

    succeeded: List[str]
    failed: List[str]
    stale_cleared: List[str]


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


async def clear_stale_markets(
    redis: "Redis",
    stale_tickers: Set[str],
    algo: str,
    key_builder: Callable[[str], str],
) -> List[str]:
    """Clear stale markets owned by this algo.

    Removes {algo}:t_yes_bid, {algo}:t_yes_ask, algo, direction fields
    and publishes event updates.

    Args:
        redis: Redis client
        stale_tickers: Set of tickers to clear
        algo: Algorithm name
        key_builder: Function to build market key from ticker

    Returns:
        List of tickers that were cleared
    """
    cleared: List[str] = []
    bid_field = algo_field(algo, "t_yes_bid")
    ask_field = algo_field(algo, "t_yes_ask")

    for ticker in stale_tickers:
        market_key = key_builder(ticker)

        # Verify this algo still owns it before clearing
        current_algo = await get_market_algo(redis, market_key)
        if current_algo != algo:
            logger.debug("Skipping clear for %s: owned by %s, not %s", ticker, current_algo, algo)
            continue

        await ensure_awaitable(redis.hdel(market_key, bid_field, ask_field, "algo", "direction"))
        cleared.append(ticker)

        try:
            await _publish_market_event_update(redis, market_key, ticker)
        except (RuntimeError, ConnectionError, OSError):  # policy_guard: allow-silent-handler
            pass

    if cleared:
        logger.info("Cleared %d stale markets for algo %s", len(cleared), algo)

    return cleared


async def update_and_clear_stale(
    redis: "Redis",
    signals: Dict[str, Dict[str, Any]],
    algo: str,
    key_builder: Callable[[str], str],
    scan_pattern: str,
) -> AlgoUpdateResult:
    """Update theoretical prices and clear stale markets atomically.

    This is the main entry point for algos to update their signals.

    1. Write {algo}:t_yes_* for each signal
    2. Claim ownership if unowned, compute direction if owner
    3. Publish event updates
    4. Scan for algo-owned markets
    5. Clear stale (owned but not in signals)

    Args:
        redis: Redis client
        signals: Dict of {ticker: {"t_yes_bid": X, "t_yes_ask": Y}}
        algo: Algorithm name
        key_builder: Function to build market key from ticker
        scan_pattern: Pattern to scan for owned markets (e.g., "markets:kalshi:*")

    Returns:
        AlgoUpdateResult with succeeded, failed, and stale_cleared lists
    """
    if algo not in VALID_ALGOS:
        raise ValueError(f"Invalid algo '{algo}'. Must be one of: {sorted(VALID_ALGOS)}")

    succeeded: List[str] = []
    failed: List[str] = []

    # Step 1-3: Write signals
    for ticker, data in signals.items():
        t_yes_bid = data.get("t_yes_bid")
        t_yes_ask = data.get("t_yes_ask")

        if t_yes_bid is None and t_yes_ask is None:
            failed.append(ticker)
            continue

        market_key = key_builder(ticker)
        try:
            await _write_theoretical_prices(redis, market_key, algo, t_yes_bid, t_yes_ask, ticker)
            succeeded.append(ticker)
        except (RuntimeError, ConnectionError, OSError):
            logger.exception("Failed to write signal for %s", ticker)
            failed.append(ticker)
            raise

    # Step 4: Scan for owned markets
    owned_tickers = await scan_algo_owned_markets(redis, scan_pattern, algo)

    # Step 5: Clear stale (owned but not in current signals)
    current_tickers = set(signals.keys())
    stale_tickers = owned_tickers - current_tickers
    stale_cleared = await clear_stale_markets(redis, stale_tickers, algo, key_builder)

    logger.info(
        "Algo %s: updated %d, failed %d, cleared %d stale",
        algo,
        len(succeeded),
        len(failed),
        len(stale_cleared),
    )

    return AlgoUpdateResult(succeeded=succeeded, failed=failed, stale_cleared=stale_cleared)


__all__ = [
    "algo_field",
    "AlgoUpdateResult",
    "batch_update_market_signals",
    "BatchUpdateResult",
    "clear_algo_ownership",
    "clear_stale_markets",
    "compute_direction",
    "get_market_algo",
    "get_rejection_stats",
    "MarketUpdateResult",
    "request_market_update",
    "scan_algo_owned_markets",
    "update_and_clear_stale",
    "VALID_ALGOS",
]
