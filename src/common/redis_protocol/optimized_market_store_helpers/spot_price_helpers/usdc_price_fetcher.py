"""USDC bid/ask price fetching with validation"""

from __future__ import annotations

import logging

from ....redis_schema import DeribitInstrumentKey, DeribitInstrumentType
from ....utils.pricing import validate_usdc_bid_ask_prices
from ...atomic_redis_operations_helpers.data_fetcher import RedisDataValidationError
from ...error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class UsdcPriceFetcher:
    """Fetches and validates USDC bid/ask prices"""

    def __init__(self, market_data_retriever, price_calculator):
        """
        Initialize USDC price fetcher

        Args:
            market_data_retriever: MarketDataRetriever instance
            price_calculator: PriceCalculator instance
        """
        self.market_data_retriever = market_data_retriever
        self.price_calculator = price_calculator

    async def get_usdc_bid_ask_prices(self, currency: str, atomic_ops=None) -> tuple[float, float]:
        """
        Return validated bid/ask prices for the currency's USDC spot pair

        Args:
            currency: Currency symbol (BTC or ETH)
            atomic_ops: Optional AtomicRedisOperations instance

        Returns:
            Tuple of (validated_bid, validated_ask)

        Raises:
            ValueError: If market data is invalid
            REDIS_ERRORS: On Redis failures
        """
        try:
            market_data = await self.market_data_retriever.get_usdc_market_data(currency, atomic_ops)

            bid_price, ask_price = self.price_calculator.extract_bid_ask_prices(market_data, currency)

            validated_bid, validated_ask = validate_usdc_bid_ask_prices(bid_price, ask_price)

            market_key = DeribitInstrumentKey(
                instrument_type=DeribitInstrumentType.SPOT,
                currency=currency.upper(),
                quote_currency="USDC",
            ).key()

            logger.debug(
                "Validated USDC bid/ask for %s: bid=%s, ask=%s (key=%s)",
                currency,
                validated_bid,
                validated_ask,
                market_key,
            )

        except ValueError:
            logger.exception("Invalid USDC bid/ask data for %s: %s")
            raise
        except RedisDataValidationError as exc:
            logger.debug("USDC bid/ask prices not available for %s: %s", currency, exc)
            raise
        except REDIS_ERRORS as exc:
            logger.error("Error getting USDC bid/ask prices for %s: %s", currency, exc, exc_info=True)
            raise
        else:
            return validated_bid, validated_ask
