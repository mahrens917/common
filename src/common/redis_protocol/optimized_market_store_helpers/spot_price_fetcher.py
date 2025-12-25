"""
Spot price fetching for OptimizedMarketStore
"""

from __future__ import annotations

import logging
from typing import Optional

from ..error_types import REDIS_ERRORS
from .spot_price_helpers import MarketDataRetriever, PriceCalculator, UsdcPriceFetcher

logger = logging.getLogger(__name__)


class SpotPriceFetcher:
    """Fetches spot prices and USDC bid/ask prices from Redis"""

    def __init__(self, redis_getter, atomic_ops):
        """
        Initialize spot price fetcher

        Args:
            redis_getter: Async function that returns Redis client
            atomic_ops: AtomicRedisOperations instance for safe reads
        """
        self._get_redis = redis_getter
        self.atomic_ops = atomic_ops

        # Initialize helpers
        self._market_data_retriever = MarketDataRetriever(redis_getter)
        self._price_calculator = PriceCalculator()
        self._usdc_price_fetcher = UsdcPriceFetcher(self._market_data_retriever, self._price_calculator)

    async def get_spot_price(self, currency: str) -> Optional[float]:
        """
        Get spot price from Deribit market data using bid/ask mid-price

        Args:
            currency: Currency symbol (BTC or ETH)

        Returns:
            Spot price calculated from market bid/ask mid-price or None if not found
        """
        try:
            market_data = await self._market_data_retriever.get_spot_market_data(currency)
            spot_price = self._price_calculator.calculate_spot_price(market_data, currency)

        except ValueError:
            logger.exception("Invalid market data for %s: %s")
            raise
        except REDIS_ERRORS as exc:
            logger.error("Error getting spot price for %s: %s", currency, exc, exc_info=True)
            raise
        else:
            return spot_price

    async def get_usdc_bid_ask_prices(self, currency: str) -> tuple[float, float]:
        """Return bid/ask prices for the currency's USDC spot pair."""
        return await self._usdc_price_fetcher.get_usdc_bid_ask_prices(currency, self.atomic_ops)
