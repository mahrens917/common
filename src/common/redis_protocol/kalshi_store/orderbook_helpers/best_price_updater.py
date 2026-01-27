"""Update best bid/ask prices from orderbook data."""

from redis.asyncio import Redis

from ....market_filters.kalshi import extract_best_ask, extract_best_bid
from ...typing import ensure_awaitable
from .side_data_updater import SideDataUpdater
from .snapshot_processor_helpers.redis_storage import store_optional_field as store_optional_field_core


class BestPriceUpdater:
    """Updates best bid/ask prices from orderbook sides.

    Note: Tracker is responsible for computing and setting direction.
    """

    @staticmethod
    async def store_optional_field(redis: Redis, market_key: str, field: str, value: object) -> None:
        """Backward-compatible wrapper for storing optional hash fields."""
        await store_optional_field_core(redis, market_key, field, value)

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
