"""Redis IO helpers for DeribitInstrumentIndex startup initialization.

Extracted from DeribitInstrumentIndex to keep the main class within
the structure_guard line limit. These functions are only called during
startup — not on the hot path.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

_SCAN_BATCH_SIZE = 10000


async def load_currency_keys(market_store: Any, currency: str) -> tuple[Any, set[str]]:
    """Scan Redis for all Deribit keys matching a currency.

    Returns the redis client and set of matching keys.
    """
    redis_client = await market_store.get_redis_client()
    pattern = f"markets:deribit:*:{currency.upper()}*"
    keys: set[str] = set()
    cursor = 0
    while True:
        cursor, batch = await redis_client.scan(cursor=cursor, match=pattern, count=_SCAN_BATCH_SIZE)
        for k in batch:
            keys.add(k.decode("utf-8") if isinstance(k, bytes) else k)
        if cursor == 0:
            break
    return redis_client, keys


async def fetch_all_hashes(redis_client: Any, keys: list[str]) -> Dict[str, Dict[Any, Any]]:
    """Pipeline HGETALL for a list of keys. Returns key -> hash data mapping."""
    result: Dict[str, Dict[Any, Any]] = {}
    async with redis_client.pipeline() as pipe:
        for key in keys:
            pipe.hgetall(key)
        responses = await pipe.execute()
    for key, data in zip(keys, responses):
        result[key] = data
    return result


def register_loaded_data(
    data_map: Dict[str, Dict[Any, Any]],
    instruments: Dict[str, Dict[str, str]],
    register_key: Callable[[str, Dict[str, str]], None],
) -> None:
    """Decode and register all fetched instrument data into the index."""
    for key, data in data_map.items():
        if not data:
            continue
        decoded = decode_hash(data)
        decoded["instrument_key"] = key
        instruments[key] = decoded
        register_key(key, decoded)


def decode_hash(raw: Dict[Any, Any]) -> Dict[str, str]:
    """Decode Redis hash bytes to strings."""
    decoded: Dict[str, str] = {}
    for k, v in raw.items():
        str_key = k.decode("utf-8") if isinstance(k, bytes) else str(k)
        str_val = v.decode("utf-8") if isinstance(v, bytes) else str(v)
        decoded[str_key] = str_val
    return decoded


__all__ = ["decode_hash", "fetch_all_hashes", "load_currency_keys", "register_loaded_data"]
