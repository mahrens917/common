"""
Market Update API

Provides algo-aware market update functionality.
All algos (whale, peak, edge, pdf, weather, crossarb, dutch, strike, total)
use this API to update theoretical prices.

Field naming convention:
  - {algo}:t_bid, {algo}:t_ask - namespaced theoretical prices per algo

Note: Tracker is responsible for setting algo/direction fields based on
which algo wins ownership and the computed trading direction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from .market_update_api_helpers import (
    PriceSignal,
    add_signal_to_pipeline,
    algo_field,
    build_market_signals,
    build_signal_mapping,
    clear_stale_markets,
    compute_direction,
    filter_valid_signals,
    get_rejection_stats,
    publish_market_event_update,
    scan_algo_active_markets,
    validate_algo_name,
    write_theoretical_prices,
)
from .retry import RedisRetryError, with_redis_retry
from .typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_PRICE_FIELDS = frozenset(("t_bid", "t_ask"))


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
    t_bid: Optional[float],
    t_ask: Optional[float],
) -> MarketUpdateResult:
    """
    Update theoretical prices for a market using namespaced fields.

    Writes {algo}:t_bid and {algo}:t_ask fields only.
    Tracker is responsible for setting algo/direction fields.

    Args:
        redis: Redis client
        market_key: Redis key for the market (e.g., markets:kalshi:weather:KXHIGH-KDCA-202501)
        algo: Algorithm name (whale, peak, edge, pdf, weather, crossarb, dutch, strike, total)
        t_bid: Theoretical bid price (can be None to skip)
        t_ask: Theoretical ask price (can be None to skip)

    Returns:
        MarketUpdateResult with success status
    """
    if t_bid is None and t_ask is None:
        return MarketUpdateResult(success=False, rejected=False, reason="no_prices_provided", owning_algo=None)

    display_ticker = market_key.split(":")[-1]

    price_signal = PriceSignal(t_bid=t_bid, t_ask=t_ask)
    await write_theoretical_prices(redis, market_key, algo, price_signal, display_ticker)

    return MarketUpdateResult(success=True, rejected=False, reason=None, owning_algo=None)


@dataclass(frozen=True)
class BatchUpdateResult:
    """Result of a batch market update."""

    succeeded: List[str]
    failed: List[str]


async def batch_update_market_signals(
    redis: "Redis",
    signals: Dict[str, Dict[str, Any]],
    algo: str,
    key_builder: Any,
) -> BatchUpdateResult:
    """Atomically update theoretical prices for multiple markets using Redis transactions.

    Writes {algo}:t_bid and {algo}:t_ask fields only.
    Tracker is responsible for setting algo/direction fields.
    """
    if not signals:
        return BatchUpdateResult(succeeded=[], failed=[])

    market_signals = build_market_signals(signals, algo, key_builder)
    valid_signals, failed = filter_valid_signals(market_signals)

    if not valid_signals:
        return BatchUpdateResult(succeeded=[], failed=failed)

    # Bid-only signals (t_ask is None) are written first so that the pipeline
    # processes simpler updates before two-sided ones; ticker breaks ties deterministically.
    sorted_signals = sorted(valid_signals, key=lambda s: (s.t_ask is not None, s.ticker))

    return await _execute_batch_transaction(redis, sorted_signals, failed, algo)


async def _execute_batch_transaction(
    redis: "Redis",
    sorted_signals: List[Any],
    failed: List[str],
    algo: str,
) -> BatchUpdateResult:
    """Execute the batch transaction and publish event updates."""
    succeeded: List[str] = []
    sig_mappings = [(sig, build_signal_mapping(sig, algo)) for sig in sorted_signals]
    bid_key = algo_field(algo, "t_bid")
    ask_key = algo_field(algo, "t_ask")

    async def _build_and_execute_pipeline() -> None:
        pipe_inner = redis.pipeline(transaction=True)
        for sig, mapping in sig_mappings:
            add_signal_to_pipeline(pipe_inner, sig, mapping)
        await ensure_awaitable(pipe_inner.execute())

    try:
        await with_redis_retry(
            _build_and_execute_pipeline,
            context=f"pipeline_batch_update:{algo}",
        )
        succeeded = [sig.ticker for sig in sorted_signals]
        logger.debug("Batch updated %d markets atomically for algo %s", len(succeeded), algo)
    except (RuntimeError, ConnectionError, OSError):
        logger.exception("Failed to execute batch update for algo %s", algo)
        raise

    for sig, mapping in sig_mappings:
        price_signal = PriceSignal(
            t_bid=mapping.get(bid_key),
            t_ask=mapping.get(ask_key),
        )
        try:
            await with_redis_retry(
                lambda _s=sig, _ps=price_signal: publish_market_event_update(
                    redis,
                    _s.market_key,
                    _s.ticker,
                    algo,
                    _ps,
                ),
                context=f"publish_event:{sig.ticker}",
            )
        except RedisRetryError:  # policy_guard: allow-silent-handler
            logger.exception("Failed to publish event update for %s after retries", sig.ticker)

    return BatchUpdateResult(succeeded=succeeded, failed=failed)


@dataclass(frozen=True)
class AlgoUpdateResult:
    """Result of update_and_clear_stale operation."""

    succeeded: List[str]
    failed: List[str]
    stale_cleared: List[str]


async def _write_signals(
    redis: "Redis",
    signals: Dict[str, Dict[str, Any]],
    algo: str,
    key_builder: Callable[[str], str],
) -> tuple[List[str], List[str], set[str]]:
    """Write theoretical prices and metadata for each signal.

    Returns (succeeded, failed, metadata_field_names).
    """
    succeeded: List[str] = []
    failed: List[str] = []
    metadata_field_names: set[str] = set()

    for ticker, data in signals.items():
        t_bid = data.get("t_bid")
        t_ask = data.get("t_ask")

        if t_bid is None and t_ask is None:
            failed.append(ticker)
            continue

        market_key = key_builder(ticker)
        try:
            await write_theoretical_prices(
                redis,
                market_key,
                algo,
                PriceSignal(t_bid=t_bid, t_ask=t_ask),
                ticker,
            )
        except (RuntimeError, ConnectionError, OSError):
            logger.exception("Failed to write theoretical prices for %s", ticker)
            raise
        else:
            succeeded.append(ticker)

        metadata = {k: v for k, v in data.items() if k not in _PRICE_FIELDS}
        if metadata:
            await write_algo_metadata(redis, market_key, algo, metadata)
            metadata_field_names.update(metadata.keys())

    return succeeded, failed, metadata_field_names


async def update_and_clear_stale(
    redis: "Redis",
    signals: Dict[str, Dict[str, Any]],
    algo: str,
    key_builder: Callable[[str], str],
    scan_pattern: str,
) -> AlgoUpdateResult:
    """Update theoretical prices and clear stale markets.

    This is the main entry point for algos to update their signals.

    1. Write {algo}:t_bid and {algo}:t_ask for each signal
    2. Publish event updates to notify tracker
    3. Scan for algo-owned markets
    4. Clear stale (owned but not in signals)

    Note: Tracker is responsible for setting algo/direction fields.
    """
    succeeded, failed, metadata_field_names = await _write_signals(
        redis,
        signals,
        algo,
        key_builder,
    )

    owned_tickers = await scan_algo_active_markets(redis, scan_pattern, algo)
    stale_tickers = owned_tickers - set(signals.keys())
    stale_cleared = await clear_stale_markets(
        redis,
        stale_tickers,
        algo,
        key_builder,
        frozenset(metadata_field_names),
    )

    for ticker in stale_cleared:
        market_key = key_builder(ticker)
        try:
            await publish_market_event_update(redis, market_key, ticker, algo, PriceSignal())
        except RedisRetryError:  # policy_guard: allow-silent-handler
            logger.exception("Failed to publish NONE signal for stale market %s", ticker)

    logger.info(
        "Algo %s: updated %d, failed %d, cleared %d stale",
        algo,
        len(succeeded),
        len(failed),
        len(stale_cleared),
    )

    return AlgoUpdateResult(succeeded=succeeded, failed=failed, stale_cleared=stale_cleared)


async def write_algo_metadata(
    redis: "Redis",
    market_key: str,
    algo: str,
    metadata: dict[str, Any],
) -> None:
    """Write algo-specific metadata fields to a market hash.

    Builds mapping with namespaced keys: {algo}:{field} for each entry in metadata.
    Single HSET call to write all fields atomically.

    Args:
        redis: Redis client
        market_key: Redis key for the market hash
        algo: Algorithm name (validated against canonical set)
        metadata: Dict of {field_name: value} to write
    """
    validate_algo_name(algo)
    mapping = {algo_field(algo, k): str(v) for k, v in metadata.items()}
    await ensure_awaitable(redis.hset(market_key, mapping=mapping))


__all__ = [
    "algo_field",
    "AlgoUpdateResult",
    "batch_update_market_signals",
    "BatchUpdateResult",
    "clear_stale_markets",
    "compute_direction",
    "get_rejection_stats",
    "MarketUpdateResult",
    "request_market_update",
    "scan_algo_active_markets",
    "update_and_clear_stale",
    "write_algo_metadata",
]
