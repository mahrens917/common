"""Redis storage for skipped market statistics."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

from common.redis_protocol.typing import RedisClient, ensure_awaitable

from .filtering import SkippedMarketStats
from .types import SkippedMarketsInfo

logger = logging.getLogger(__name__)

REDIS_KEY = "kalshi:skipped_markets"
TTL_SECONDS = 3600  # 1 hour


def _stats_to_info(stats: SkippedMarketStats) -> SkippedMarketsInfo:
    """Convert internal stats to serializable info."""
    return SkippedMarketsInfo(
        total_skipped=stats.total_skipped,
        by_strike_type=dict(stats.by_strike_type),
        by_category=dict(stats.by_category),
    )


async def store_skipped_stats(
    redis: RedisClient,
    stats: SkippedMarketStats,
) -> None:
    """Store skipped market stats in Redis.

    Args:
        redis: Redis client
        stats: Skipped market statistics from discovery
    """
    info = _stats_to_info(stats)
    data: Dict[str, Any] = {
        "timestamp": int(time.time()),
        "total_skipped": info.total_skipped,
        "by_strike_type": info.by_strike_type,
        "by_category": info.by_category,
    }
    json_data = json.dumps(data)
    await ensure_awaitable(redis.set(REDIS_KEY, json_data, ex=TTL_SECONDS))
    logger.debug("Stored skipped market stats: %d markets", info.total_skipped)


__all__ = [
    "store_skipped_stats",
]
