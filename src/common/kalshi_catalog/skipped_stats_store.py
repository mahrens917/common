"""Redis storage for skipped market statistics."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

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


def _build_skipped_info_from_data(data: Dict[str, Any]) -> SkippedMarketsInfo:
    """Build SkippedMarketsInfo from parsed JSON data."""
    by_strike_type_value = data.get("by_strike_type")
    by_category_value = data.get("by_category")
    total_skipped_value = data.get("total_skipped")

    by_strike_type: Dict[str, List[str]] = {}
    if by_strike_type_value is not None:
        by_strike_type = by_strike_type_value

    by_category: Dict[str, int] = {}
    if by_category_value is not None:
        by_category = by_category_value

    total_skipped = 0
    if total_skipped_value is not None:
        total_skipped = total_skipped_value

    return SkippedMarketsInfo(
        total_skipped=total_skipped,
        by_strike_type=by_strike_type,
        by_category=by_category,
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


async def get_skipped_stats(redis: RedisClient) -> Optional[SkippedMarketsInfo]:
    """Retrieve skipped market stats from Redis.

    Args:
        redis: Redis client

    Returns:
        SkippedMarketsInfo if available, None otherwise
    """
    raw = await ensure_awaitable(redis.get(REDIS_KEY))
    if raw is None:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return _build_skipped_info_from_data(data)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:  # policy_guard: allow-silent-handler
        logger.warning("Failed to parse skipped stats from Redis: %s", exc)
        return None


__all__ = [
    "get_skipped_stats",
    "store_skipped_stats",
]
