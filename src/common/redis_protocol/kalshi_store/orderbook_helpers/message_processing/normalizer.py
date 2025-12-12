"""JSON normalization for orderbook snapshots."""

from typing import Any, Dict

import orjson
from redis.asyncio import Redis

from ....typing import ensure_awaitable


async def normalize_snapshot_json(redis: Redis, market_key: str) -> None:
    """Normalize stored orderbook JSON for deterministic tests."""
    for field_name in ("yes_bids", "yes_asks"):
        payload = await ensure_awaitable(redis.hget(market_key, field_name))
        if not payload:
            continue
        try:
            decoded = orjson.loads(payload)
        except orjson.JSONDecodeError:  # policy_guard: allow-silent-handler
            continue

        updated = normalize_price_map(decoded)
        if updated != decoded:
            await ensure_awaitable(
                redis.hset(
                    market_key,
                    field_name,
                    orjson.dumps(updated).decode(),
                )
            )


def normalize_price_map(data: Dict[Any, Any]) -> Dict[str, Any]:
    """Remove redundant trailing zeros in orderbook snapshots."""
    normalized: Dict[str, Any] = {}
    for key, value in data.items():
        try:
            if isinstance(key, str) and "." not in key:
                normalized_key = key
            elif isinstance(key, (int, float)) and not isinstance(key, bool):
                normalized_key = str(int(key)) if float(key).is_integer() else f"{float(key):.1f}"
            else:
                normalized_key = f"{float(key):.1f}"
        except (TypeError, ValueError):
            normalized_key = str(key)

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            numeric_value = value
        normalized[normalized_key] = numeric_value
    return normalized
