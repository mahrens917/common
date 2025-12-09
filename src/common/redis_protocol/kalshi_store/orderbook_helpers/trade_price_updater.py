"""Update trade prices from current best prices."""

from redis.asyncio import Redis

from ...typing import ensure_awaitable
from .field_converter import FieldConverter


class TradePriceUpdater:
    """Updates trade prices from best bid/ask."""

    def __init__(self, update_callback):
        """Initialize with callback function."""
        self._update_callback = update_callback

    async def update_trade_prices(self, redis: Redis, market_key: str, market_ticker: str) -> None:
        """Update trade prices callback with current best prices."""
        yes_bid_raw = await ensure_awaitable(redis.hget(market_key, "yes_bid"))
        yes_ask_raw = await ensure_awaitable(redis.hget(market_key, "yes_ask"))

        decoded_yes_bid = (
            yes_bid_raw.decode("utf-8", "ignore") if isinstance(yes_bid_raw, bytes) else yes_bid_raw
        )
        decoded_yes_ask = (
            yes_ask_raw.decode("utf-8", "ignore") if isinstance(yes_ask_raw, bytes) else yes_ask_raw
        )

        parsed_yes_bid = FieldConverter.convert_numeric_field(decoded_yes_bid)
        parsed_yes_ask = FieldConverter.convert_numeric_field(decoded_yes_ask)

        if parsed_yes_bid is not None and parsed_yes_ask is not None:
            await self._update_callback(market_ticker, parsed_yes_bid, parsed_yes_ask)
