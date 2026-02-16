"""
Algo Stats API

Provides centralized algo statistics storage in Redis.
All algos (whale, peak, edge, pdf, weather) can write their stats here,
and tracker can read them for unified status reporting.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Optional

from .typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

ALGO_STATS_KEY_PREFIX = "algo_stats"
ALGO_STATS_TTL_SECONDS = 86400  # 24 hours


@dataclass
class AlgoStatsData:
    """Statistics for a single algorithm."""

    algo: str = ""
    events_processed: int = 0
    signals_generated: int = 0
    signals_written: int = 0
    ownership_rejections: int = 0
    markets_evaluated: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, str]:
        """Convert to Redis dict (all string values)."""
        return {k: str(v) for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "AlgoStatsData":
        """Create from Redis dict with fields that exist."""
        kwargs: Dict[str, str | int] = {}
        if "algo" in data:
            kwargs["algo"] = data["algo"]
        if "events_processed" in data:
            kwargs["events_processed"] = int(data["events_processed"])
        if "signals_generated" in data:
            kwargs["signals_generated"] = int(data["signals_generated"])
        if "signals_written" in data:
            kwargs["signals_written"] = int(data["signals_written"])
        if "ownership_rejections" in data:
            kwargs["ownership_rejections"] = int(data["ownership_rejections"])
        if "markets_evaluated" in data:
            kwargs["markets_evaluated"] = int(data["markets_evaluated"])
        if "last_updated" in data:
            kwargs["last_updated"] = data["last_updated"]
        return cls(**kwargs)  # type: ignore[arg-type]


def _build_stats_key(algo: str) -> str:
    """Build Redis key for algo stats."""
    return f"{ALGO_STATS_KEY_PREFIX}:{algo}"


async def write_algo_stats(
    redis: "Redis",
    algo: str,
    events_processed: int = 0,
    signals_generated: int = 0,
    signals_written: int = 0,
    ownership_rejections: int = 0,
    markets_evaluated: int = 0,
) -> bool:
    """
    Write algo statistics to Redis.

    Stats are cumulative - this overwrites the current values.
    Call increment_algo_stats for incremental updates.

    Args:
        redis: Redis client
        algo: Algorithm name (whale, peak, edge, pdf, weather)
        events_processed: Number of events processed
        signals_generated: Number of signals generated
        signals_written: Number of signals successfully written
        ownership_rejections: Number of ownership rejections
        markets_evaluated: Number of markets evaluated

    Returns:
        True if write succeeded
    """
    stats_key = _build_stats_key(algo)
    stats = AlgoStatsData(
        algo=algo,
        events_processed=events_processed,
        signals_generated=signals_generated,
        signals_written=signals_written,
        ownership_rejections=ownership_rejections,
        markets_evaluated=markets_evaluated,
        last_updated=datetime.now(timezone.utc).isoformat(),
    )

    await ensure_awaitable(redis.hset(stats_key, mapping=stats.to_dict()))
    await ensure_awaitable(redis.expire(stats_key, ALGO_STATS_TTL_SECONDS))
    logger.debug("Wrote stats for algo %s: %s", algo, stats)
    return True


async def increment_algo_stats(
    redis: "Redis",
    algo: str,
    events_processed: int = 0,
    signals_generated: int = 0,
    signals_written: int = 0,
    ownership_rejections: int = 0,
    markets_evaluated: int = 0,
) -> bool:
    """
    Increment algo statistics in Redis.

    Uses HINCRBY for atomic increments.

    Args:
        redis: Redis client
        algo: Algorithm name
        events_processed: Increment for events processed
        signals_generated: Increment for signals generated
        signals_written: Increment for signals written
        ownership_rejections: Increment for ownership rejections
        markets_evaluated: Increment for markets evaluated

    Returns:
        True if increment succeeded
    """
    stats_key = _build_stats_key(algo)

    # Use pipeline for atomic updates
    pipe = redis.pipeline()

    if events_processed:
        pipe.hincrby(stats_key, "events_processed", events_processed)
    if signals_generated:
        pipe.hincrby(stats_key, "signals_generated", signals_generated)
    if signals_written:
        pipe.hincrby(stats_key, "signals_written", signals_written)
    if ownership_rejections:
        pipe.hincrby(stats_key, "ownership_rejections", ownership_rejections)
    if markets_evaluated:
        pipe.hincrby(stats_key, "markets_evaluated", markets_evaluated)

    # Always update algo name and timestamp
    pipe.hset(stats_key, "algo", algo)
    pipe.hset(stats_key, "last_updated", datetime.now(timezone.utc).isoformat())
    pipe.expire(stats_key, ALGO_STATS_TTL_SECONDS)

    await pipe.execute()

    logger.debug(
        "Incremented stats for %s: events=%d, signals=%d, written=%d",
        algo,
        events_processed,
        signals_generated,
        signals_written,
    )
    return True


async def read_algo_stats(redis: "Redis", algo: str) -> Optional[AlgoStatsData]:
    """
    Read algo statistics from Redis.

    Args:
        redis: Redis client
        algo: Algorithm name

    Returns:
        AlgoStatsData if found, None otherwise
    """
    stats_key = _build_stats_key(algo)

    data = await ensure_awaitable(redis.hgetall(stats_key))
    if not data:
        return None

    # Decode bytes if needed
    decoded = {}
    for k, v in data.items():
        key = k.decode() if isinstance(k, bytes) else str(k)
        val = v.decode() if isinstance(v, bytes) else str(v)
        decoded[key] = val

    return AlgoStatsData.from_dict(decoded)


async def read_all_algo_stats(redis: "Redis") -> Dict[str, AlgoStatsData]:
    """
    Read statistics for all known algos.

    Args:
        redis: Redis client

    Returns:
        Dict mapping algo name to stats
    """
    algos = ["whale", "peak", "edge", "pdf", "weather"]
    results: Dict[str, AlgoStatsData] = {}

    for algo in algos:
        stats = await read_algo_stats(redis, algo)
        if stats:
            results[algo] = stats

    return results


async def reset_algo_stats(redis: "Redis", algo: str) -> bool:
    """
    Reset statistics for an algo (delete the key).

    Args:
        redis: Redis client
        algo: Algorithm name

    Returns:
        True if reset succeeded
    """
    stats_key = _build_stats_key(algo)

    await ensure_awaitable(redis.delete(stats_key))
    logger.info("Reset stats for algo %s", algo)
    return True


__all__ = [
    "AlgoStatsData",
    "write_algo_stats",
    "increment_algo_stats",
    "read_algo_stats",
    "read_all_algo_stats",
    "reset_algo_stats",
    "ALGO_STATS_KEY_PREFIX",
]
