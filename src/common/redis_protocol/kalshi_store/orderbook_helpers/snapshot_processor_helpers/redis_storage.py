"""Redis storage operations for snapshot processor."""

from typing import Any, Dict

import orjson
from redis.asyncio import Redis

from ....typing import ensure_awaitable


async def store_optional_field(redis: Redis, market_key: str, field: str, value: Any) -> None:
    """Persist a Redis hash field only when a value exists."""
    if value is None:
        await ensure_awaitable(redis.hdel(market_key, field))
        return
    await ensure_awaitable(redis.hset(market_key, field, str(value)))


async def store_hash_fields(redis: Redis, market_key: str, hash_data: Dict[str, str], timestamp: str) -> None:
    """Store all hash fields in Redis atomically."""
    fields = {k: v for k, v in hash_data.items() if k != "timestamp"}
    fields["timestamp"] = timestamp
    await ensure_awaitable(redis.hset(market_key, mapping=fields))


async def store_best_prices(
    redis: Redis,
    market_key: str,
    yes_bid_price: Any,
    yes_ask_price: Any,
    yes_bid_size: Any,
    yes_ask_size: Any,
) -> None:
    """Store best bid/ask prices and sizes atomically."""
    field_values = [
        ("yes_bid", yes_bid_price),
        ("yes_ask", yes_ask_price),
        ("yes_bid_size", yes_bid_size),
        ("yes_ask_size", yes_ask_size),
    ]
    fields_to_set = {name: str(val) for name, val in field_values if val is not None}
    fields_to_del = [name for name, val in field_values if val is None]
    if fields_to_set:
        await ensure_awaitable(redis.hset(market_key, mapping=fields_to_set))
    if fields_to_del:
        await ensure_awaitable(redis.hdel(market_key, *fields_to_del))


def build_hash_data(orderbook_sides: Dict[str, Any], timestamp: str) -> Dict[str, str]:
    """Build hash data for Redis storage."""
    hash_data = {side_name: orjson.dumps(side_data).decode() for side_name, side_data in orderbook_sides.items()}
    hash_data["timestamp"] = timestamp
    return hash_data
