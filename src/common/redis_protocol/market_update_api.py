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

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set

from .market_update_api_helpers import (
    REJECTION_KEY_PREFIX,
    add_signal_to_pipeline,
    algo_field,
    build_market_signals,
    build_signal_mapping,
    check_ownership,
    clear_algo_ownership,
    clear_stale_markets,
    compute_direction,
    fetch_kalshi_prices,
    get_market_algo,
    get_rejection_stats,
    parse_int,
    publish_market_event_update,
    scan_algo_owned_markets,
    write_theoretical_prices,
)
from .retry import with_redis_retry
from .typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

VALID_ALGOS = frozenset({"whale", "peak", "edge", "pdf", "weather"})


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

    await write_theoretical_prices(redis, market_key, algo, t_yes_bid, t_yes_ask, display_ticker)

    current_owner = await get_market_algo(redis, market_key)

    return MarketUpdateResult(success=True, rejected=False, reason=None, owning_algo=current_owner)


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
    if algo not in VALID_ALGOS:
        raise ValueError(f"Invalid algo '{algo}'. Must be one of: {sorted(VALID_ALGOS)}")

    if not signals:
        return BatchUpdateResult(succeeded=[], rejected=[], failed=[])

    from .market_update_api_helpers import filter_allowed_signals

    market_signals = build_market_signals(signals, algo, key_builder)
    allowed, rejected, failed = await filter_allowed_signals(redis, market_signals, algo, check_ownership)

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
    kalshi_bid = parse_int(prices[0])
    kalshi_ask = parse_int(prices[1])
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
        await with_redis_retry(
            lambda: ensure_awaitable(pipe.execute()),
            context=f"pipeline_batch_update:{algo}",
        )
        succeeded = [sig.ticker for sig in sorted_signals]
        logger.debug("Batch updated %d markets atomically for algo %s", len(succeeded), algo)
    except (RuntimeError, ConnectionError, OSError):
        logger.exception("Failed to execute batch update for algo %s", algo)
        failed.extend(sig.ticker for sig in sorted_signals)
        raise

    for sig in sorted_signals:
        try:
            await publish_market_event_update(redis, sig.market_key, sig.ticker)
        except (RuntimeError, ConnectionError, OSError):  # Expected, non-critical  # policy_guard: allow-silent-handler
            pass

    return BatchUpdateResult(succeeded=succeeded, rejected=rejected, failed=failed)


@dataclass(frozen=True)
class AlgoUpdateResult:
    """Result of update_and_clear_stale operation."""

    succeeded: List[str]
    failed: List[str]
    stale_cleared: List[str]


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

    for ticker, data in signals.items():
        t_yes_bid = data.get("t_yes_bid")
        t_yes_ask = data.get("t_yes_ask")

        if t_yes_bid is None and t_yes_ask is None:
            failed.append(ticker)
            continue

        market_key = key_builder(ticker)
        try:
            await write_theoretical_prices(redis, market_key, algo, t_yes_bid, t_yes_ask, ticker)
            succeeded.append(ticker)
        except (RuntimeError, ConnectionError, OSError):
            logger.exception("Failed to write signal for %s", ticker)
            failed.append(ticker)
            raise

    owned_tickers = await scan_algo_owned_markets(redis, scan_pattern, algo)

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
