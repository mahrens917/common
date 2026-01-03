"""Update best bid/ask prices from orderbook data."""

from typing import Optional

from redis.asyncio import Redis

from ....market_filters.kalshi import extract_best_ask, extract_best_bid
from ...market_update_api import compute_direction
from ...typing import ensure_awaitable
from .side_data_updater import SideDataUpdater
from .snapshot_processor_helpers.redis_storage import store_optional_field as store_optional_field_core


def _parse_int_optional(value: object) -> Optional[int]:
    """Parse value to int, returning None for missing/empty."""
    if value is None or value in {"", b""}:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return int(float(value))
    return None


class BestPriceUpdater:
    """Updates best bid/ask prices from orderbook sides."""

    @staticmethod
    async def store_optional_field(redis: Redis, market_key: str, field: str, value: object) -> None:
        """Backward-compatible wrapper for storing optional hash fields."""
        await store_optional_field_core(redis, market_key, field, value)

    @staticmethod
    async def _recompute_direction(redis: Redis, market_key: str) -> None:
        """Recompute and store direction based on current prices and theoretical values."""
        fields = await ensure_awaitable(
            redis.hmget(market_key, ["yes_bid", "yes_ask", "t_yes_bid", "t_yes_ask"])
        )
        kalshi_bid = _parse_int_optional(fields[0])
        kalshi_ask = _parse_int_optional(fields[1])
        t_yes_bid = _parse_int_optional(fields[2])
        t_yes_ask = _parse_int_optional(fields[3])

        if t_yes_bid is None and t_yes_ask is None:
            return

        direction = compute_direction(
            t_yes_bid,
            t_yes_ask,
            kalshi_bid if kalshi_bid is not None else 0,
            kalshi_ask if kalshi_ask is not None else 0,
        )
        await ensure_awaitable(redis.hset(market_key, "direction", direction))

    @staticmethod
    async def update_from_side(redis: Redis, market_key: str, side_field: str) -> None:
        """Update best prices from orderbook side data."""
        side_json = await ensure_awaitable(redis.hget(market_key, side_field))
        side_data = SideDataUpdater.parse_side_data(side_json)

        if side_field == "yes_bids":
            best_price, best_size = extract_best_bid(side_data)
            await BestPriceUpdater.store_optional_field(redis, market_key, "yes_bid", best_price)
            await BestPriceUpdater.store_optional_field(redis, market_key, "yes_bid_size", best_size)
        else:
            best_price, best_size = extract_best_ask(side_data)
            await BestPriceUpdater.store_optional_field(redis, market_key, "yes_ask", best_price)
            await BestPriceUpdater.store_optional_field(redis, market_key, "yes_ask_size", best_size)

        await BestPriceUpdater._recompute_direction(redis, market_key)
