from __future__ import annotations

"""Deribit store exposing convenience helpers over the optimized market store."""

from typing import Any, Tuple

from src.common.exceptions import DataError, ValidationError

from ..redis_schema import DeribitInstrumentKey, DeribitInstrumentType
from .optimized_market_store import OptimizedMarketStore


class DeribitStore(OptimizedMarketStore):
    """Thin wrapper around :class:`OptimizedMarketStore` exposing convenience helpers."""

    def __init__(self, redis: Any | None = None):
        if redis is None:
            raise TypeError(
                "DeribitStore requires an explicit Redis client; use OptimizedMarketStore.create() for pool-based usage."
            )
        super().__init__(redis)

    async def get_usdc_bid_ask_prices(self, currency: str) -> Tuple[float, float]:
        """Return bid/ask tuple for the currency's USDC pair."""

        pair_key = DeribitInstrumentKey(
            instrument_type=DeribitInstrumentType.SPOT,
            currency=currency,
            quote_currency="USDC",
        ).key()
        redis = await self._get_redis()

        if self.atomic_ops:
            market_data = await self.atomic_ops.safe_market_data_read(
                pair_key, required_fields=["best_bid", "best_ask"]
            )
        else:
            market_data = await redis.hgetall(pair_key)

        if not market_data:
            raise DataError(
                f"USDC pair market data not available for {currency}; key '{pair_key}' missing"
            )

        bid_str = market_data.get("best_bid")
        ask_str = market_data.get("best_ask")
        if bid_str is None or ask_str is None:
            raise DataError(
                f"USDC pair market data incomplete for {currency}; bid='{bid_str}', ask='{ask_str}'"
            )

        try:
            return float(bid_str), float(ask_str)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"USDC pair market data invalid for {currency}; bid='{bid_str}', ask='{ask_str}'"
            ) from exc

    async def get_usdc_micro_price(self, currency: str) -> float:
        """Return micro-price for the currency's USDC pair."""

        pair_key = DeribitInstrumentKey(
            instrument_type=DeribitInstrumentType.SPOT,
            currency=currency,
            quote_currency="USDC",
        ).key()
        redis = await self._get_redis()

        required_fields = ["best_bid", "best_ask", "best_bid_size", "best_ask_size"]
        market_data = None

        if self.atomic_ops:
            market_data = await self.atomic_ops.safe_market_data_read(
                pair_key, required_fields=required_fields
            )
        else:
            market_data = await redis.hgetall(pair_key)

        if not market_data:
            raise DataError(
                f"USDC pair market data not available for {currency}; key '{pair_key}' missing"
            )

        missing = [field for field in required_fields if market_data.get(field) is None]
        if missing:
            raise DataError(f"USDC pair market data incomplete for {currency}; missing {missing}")

        try:
            from ..utils.pricing import calculate_usdc_micro_price

            bid_price = float(market_data["best_bid"])
            ask_price = float(market_data["best_ask"])
            bid_size = float(market_data["best_bid_size"])
            ask_size = float(market_data["best_ask_size"])
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"USDC pair market data invalid for {currency}; payload={market_data}"
            ) from exc

        return calculate_usdc_micro_price(bid_price, ask_price, bid_size, ask_size)


__all__ = ["DeribitStore"]
