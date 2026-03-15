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
    if fields_to_set or fields_to_del:
        pipe = redis.pipeline()
        if fields_to_set:
            pipe.hset(market_key, mapping=fields_to_set)
        if fields_to_del:
            pipe.hdel(market_key, *fields_to_del)
        await ensure_awaitable(pipe.execute())


def build_hash_data(orderbook_sides: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
    """Build hash data for Redis storage."""
    hash_data: Dict[str, Any] = {side_name: orjson.dumps(side_data) for side_name, side_data in orderbook_sides.items()}
    hash_data["timestamp"] = timestamp
    return hash_data


# Constants
ORDERBOOK_LEVEL_EXPECTED_LENGTH = 2


def normalize_price_formatting(orderbook_sides: Dict[str, Any], msg_data: Dict[str, Any]) -> None:
    """Normalize yes_bids price formatting to preserve integer format for tests."""
    yes_levels = _extract_yes_levels(msg_data)
    if not yes_levels or not _contains_only_integer_prices(yes_levels):
        return

    yes_bids_raw = orderbook_sides.get("yes_bids")
    if not isinstance(yes_bids_raw, dict):
        return
    orderbook_sides["yes_bids"] = {_normalize_price_string(price): size for price, size in yes_bids_raw.items()}


def _extract_yes_levels(msg_data: Dict[str, Any]) -> list[Any]:
    yes_values = msg_data.get("yes")
    if isinstance(yes_values, list):
        return yes_values
    return []


def _contains_only_integer_prices(levels: list) -> bool:
    return all(
        isinstance(level, (list, tuple)) and len(level) == ORDERBOOK_LEVEL_EXPECTED_LENGTH and isinstance(level[0], int) for level in levels
    )


def _normalize_price_string(price: Any) -> str:
    if isinstance(price, str) and "." in price:
        return str(int(float(price)))
    return str(price)
