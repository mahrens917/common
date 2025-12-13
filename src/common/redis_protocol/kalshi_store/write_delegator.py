"""
Write operations delegator for KalshiStore.

Handles all write operations including market data updates, interpolation results,
and trade tick processing.
"""

from typing import Any, Dict, Optional

from redis.asyncio import Redis

from common.truthy import pick_if

from .writer import KalshiMarketWriter


class WriteDelegator:
    """Handles write operations delegation."""

    def __init__(self, writer: KalshiMarketWriter, get_market_key_fn) -> None:
        """Initialize write delegator."""
        self._writer = writer
        self._get_market_key = get_market_key_fn

    async def write_enhanced_market_data(
        self,
        market_ticker: str,
        field_updates: Dict[str, Any],
    ) -> bool:
        """Write enhanced market data."""
        market_key = self._get_market_key(market_ticker)
        return await self._writer.write_enhanced_market_data(
            market_ticker,
            market_key,
            field_updates,
        )

    async def update_interpolation_results(
        self,
        currency: str,
        mapping_results: Dict[str, Dict],
    ) -> bool:
        """Update interpolation results (batch)."""
        return await self._writer.update_interpolation_results(
            currency,
            mapping_results,
            self._get_market_key,
        )

    async def get_interpolation_results(
        self,
        currency: str,
        keys: Any,
        str_func: Any,
        int_func: Any,
        float_func: Any,
    ) -> Dict[str, Dict]:
        """Get interpolation results (batch)."""
        return await self._writer.get_interpolation_results(
            currency,
            keys,
            str_func,
            int_func,
            float_func,
        )

    async def update_trade_tick(self, message: Dict) -> bool:
        """Update trade tick data."""
        from ...redis_schema import describe_kalshi_ticker

        def key_func(ticker: str) -> str:
            return describe_kalshi_ticker(ticker).key

        def map_func(msg: Any) -> Any:
            return pick_if(isinstance(msg, dict), lambda: msg, lambda: {})

        def str_func(val: Any) -> str:
            return pick_if(val is not None, lambda: str(val), lambda: "")

        return await self._writer.update_trade_tick(message, key_func, map_func, str_func)

    async def update_trade_prices_for_market(
        self,
        ticker: str,
        bid: Optional[float],
        ask: Optional[float],
    ) -> None:
        """Update trade prices for market (callback for orderbook processor)."""
        await self._writer.update_trade_prices_for_market(ticker, bid, ask)

    async def store_optional_field(self, redis: Redis, market_key: str, field: str, value: Optional[Any]) -> None:
        """Persist a Redis hash field only when a value exists."""
        await self._writer.store_optional_field(redis, market_key, field, value)
