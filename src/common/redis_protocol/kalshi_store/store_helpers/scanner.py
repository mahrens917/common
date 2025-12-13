"""Redis key scanning helpers for KalshiStore."""

from typing import List, Optional, Set

from redis.asyncio import Redis

from ....config.redis_schema import get_schema_config
from ....parsing_utils import decode_redis_key

SCHEMA = get_schema_config()


async def scan_market_keys(store, patterns: Optional[List[str]] = None) -> List[str]:
    """Scan Redis for Kalshi market keys."""
    if hasattr(store, "_reader"):
        scanner = getattr(store._reader, "_scan_market_keys", None)
        if scanner is not None:
            return await scanner(patterns)

    if not await store._ensure_redis_connection():
        raise RuntimeError("Redis connection not established for scan_market_keys")

    redis = await store._get_redis()
    target_patterns = patterns
    if not target_patterns:
        target_patterns = list()
        target_patterns.append(f"{SCHEMA.kalshi_market_prefix}:*")
    seen: Set[str] = set()
    results: List[str] = []

    for pattern in target_patterns:
        await scan_single_pattern(redis, pattern, seen, results)
    return results


async def scan_single_pattern(redis: Redis, pattern: str, seen: Set[str], results: List[str]) -> None:
    """Scan Redis for keys matching a single pattern."""
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=1000)
        add_unique_keys(keys, seen, results)
        if cursor == 0:
            break


def add_unique_keys(keys: List, seen: Set[str], results: List[str]) -> None:
    """Add unique keys to results list."""
    for raw_key in keys:
        key_str = decode_redis_key(raw_key)
        if key_str not in seen:
            seen.add(key_str)
            results.append(key_str)
