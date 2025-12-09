"""Update best bid/ask prices from orderbook data."""

from redis.asyncio import Redis

from ....market_filters.kalshi import extract_best_ask, extract_best_bid
from ...typing import ensure_awaitable
from .side_data_updater import SideDataUpdater


class BestPriceUpdater:
    """Updates best bid/ask prices from orderbook sides."""

    @staticmethod
    async def store_optional_field(redis: Redis, market_key: str, field: str, value) -> None:
        """Persist Redis hash field only when value exists."""
        if value is None:
            await ensure_awaitable(redis.hdel(market_key, field))
            return
        await ensure_awaitable(redis.hset(market_key, field, str(value)))

    @staticmethod
    async def update_from_side(redis: Redis, market_key: str, side_field: str) -> None:
        """Update best prices from orderbook side data."""
        side_json = await ensure_awaitable(redis.hget(market_key, side_field))
        side_data = SideDataUpdater.parse_side_data(side_json)

        if side_field == "yes_bids":
            best_price, best_size = extract_best_bid(side_data)
            await BestPriceUpdater.store_optional_field(redis, market_key, "yes_bid", best_price)
            await BestPriceUpdater.store_optional_field(
                redis, market_key, "yes_bid_size", best_size
            )
        else:
            best_price, best_size = extract_best_ask(side_data)
            await BestPriceUpdater.store_optional_field(redis, market_key, "yes_ask", best_price)
            await BestPriceUpdater.store_optional_field(
                redis, market_key, "yes_ask_size", best_size
            )
