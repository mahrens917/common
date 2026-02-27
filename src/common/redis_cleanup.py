"""Centralized Redis sorted set cleanup.

Prunes stale entries from sorted sets and deletes empty keys.
Run periodically by the monitor's interval executor.
"""

import logging
from typing import Any

from common.redis_protocol.config import DATA_CUTOFF_SECONDS, HISTORY_TTL_SECONDS

logger = logging.getLogger(__name__)

_REALTIME_RETENTION_SECONDS = 120
_ASOS_RETENTION_SECONDS = 48 * 3600
_DEFAULT_HISTORY_RETENTION_SECONDS = 86400
_WEATHER_STATION_RETENTION_SECONDS = 48 * 3600

# Key prefix -> retention seconds, checked in order (first match wins).
_KEY_RETENTION: list[tuple[str, int]] = [
    ("history:deribit_realtime", _REALTIME_RETENTION_SECONDS),
    ("history:kalshi_realtime", _REALTIME_RETENTION_SECONDS),
    ("history:btc", HISTORY_TTL_SECONDS),
    ("history:eth", HISTORY_TTL_SECONDS),
    ("history:crossarb:", HISTORY_TTL_SECONDS),
    ("history:asos", _ASOS_RETENTION_SECONDS),
    ("history:", _DEFAULT_HISTORY_RETENTION_SECONDS),
    ("trades:", DATA_CUTOFF_SECONDS),
    ("weather:station_history:", _WEATHER_STATION_RETENTION_SECONDS),
]

_SKIP_PREFIXES = ("balance:", "trades:by_")
_SKIP_INFIXES = (":order-",)

_SCAN_PATTERNS = ("trades:*", "history:*", "weather:station_history:*")


def _get_retention_seconds(key: str) -> int | None:
    """Return retention seconds for a key, or None to skip."""
    for prefix in _SKIP_PREFIXES:
        if key.startswith(prefix):
            return None
    for infix in _SKIP_INFIXES:
        if infix in key:
            return None
    for prefix, retention in _KEY_RETENTION:
        if key.startswith(prefix):
            return retention
    return None


async def _scan_keys(redis_client: Any, pattern: str) -> set[str]:
    """Scan Redis for keys matching a pattern."""
    found: set[str] = set()
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match=pattern, count=500)
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            found.add(key_str)
        if cursor == 0:
            break
    return found


def _build_cutoff_list(all_keys: set[str], now: float) -> list[tuple[str, float]]:
    """Build (key, cutoff_timestamp) pairs for keys with known retention."""
    result = []
    for key in all_keys:
        retention = _get_retention_seconds(key)
        if retention is not None:
            result.append((key, now - retention))
    return result


async def _prune_keys(redis_client: Any, keys_with_cutoff: list[tuple[str, float]]) -> int:
    """Remove stale entries; return count of keys that had entries removed."""
    pipe = redis_client.pipeline()
    for key, cutoff in keys_with_cutoff:
        pipe.zremrangebyscore(key, "-inf", str(cutoff))
    results = await pipe.execute()
    return sum(1 for r in results if r and r > 0)


async def _delete_empty_keys(redis_client: Any, keys_with_cutoff: list[tuple[str, float]]) -> int:
    """Delete keys with zero remaining entries; return count deleted."""
    pipe = redis_client.pipeline()
    for key, _ in keys_with_cutoff:
        pipe.zcard(key)
    card_results = await pipe.execute()
    empty_keys = [key for (key, _), card in zip(keys_with_cutoff, card_results) if card == 0]
    if not empty_keys:
        return 0
    pipe = redis_client.pipeline()
    for key in empty_keys:
        pipe.delete(key)
    await pipe.execute()
    return len(empty_keys)


async def prune_sorted_set_keys(redis_client: Any, now: float) -> int:
    """Prune stale entries from all managed sorted set keys.

    Scans for trades:*, history:*, and weather:station_history:* keys,
    removes entries older than each key's retention window, and deletes
    keys left empty after pruning.

    Returns the total number of keys affected (pruned or deleted).
    """
    all_keys: set[str] = set()
    for pattern in _SCAN_PATTERNS:
        all_keys |= await _scan_keys(redis_client, pattern)
    keys_with_cutoff = _build_cutoff_list(all_keys, now)
    if not keys_with_cutoff:
        return 0
    pruned = await _prune_keys(redis_client, keys_with_cutoff)
    deleted = await _delete_empty_keys(redis_client, keys_with_cutoff)
    total = pruned + deleted
    if total > 0:
        logger.info("Redis cleanup: pruned %d keys, deleted %d empty", pruned, deleted)
    return total
