"""Market data retrieval from Redis"""

import logging
from typing import Any, Dict

from common.exceptions import DataError

from ....redis_schema import DeribitInstrumentKey, DeribitInstrumentType
from ...atomic_redis_operations_helpers.data_fetcher import RedisDataValidationError
from ...error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class MarketDataRetriever:
    """Retrieves market data from Redis"""

    def __init__(self, redis_getter):
        """
        Initialize market data retriever

        Args:
            redis_getter: Async function that returns Redis client
        """
        self._get_redis = redis_getter

    async def get_spot_market_data(self, currency: str) -> Dict[str, Any]:
        """
        Fetch spot market data from Redis

        Args:
            currency: Currency symbol (BTC or ETH)

        Returns:
            Market data dictionary from Redis

        Raises:
            ValueError: If no market data found
            REDIS_ERRORS: On Redis failures
        """
        try:
            logger.debug("Getting Deribit market data for %s", currency)

            market_key = DeribitInstrumentKey(
                instrument_type=DeribitInstrumentType.SPOT,
                currency=currency.upper(),
                quote_currency="USDC",
            ).key()
            redis = await self._get_redis()
            market_data = await redis.hgetall(market_key)

            if not market_data:
                raise DataError(f"No Deribit market data found for {currency}")

            else:
                return market_data
        except REDIS_ERRORS as exc:
            logger.error("Error getting market data for %s: %s", currency, exc, exc_info=True)
            raise

    async def get_usdc_market_data(self, currency: str, atomic_ops=None) -> Dict[str, Any]:
        """
        Fetch USDC pair market data from Redis with optional atomic operations

        Args:
            currency: Currency symbol (BTC or ETH)
            atomic_ops: Optional AtomicRedisOperations instance for safe reads

        Returns:
            Market data dictionary from Redis

        Raises:
            ValueError: If no market data found
            REDIS_ERRORS: On Redis failures
        """
        try:
            market_key = DeribitInstrumentKey(
                instrument_type=DeribitInstrumentType.SPOT,
                currency=currency.upper(),
                quote_currency="USDC",
            ).key()
            redis = await self._get_redis()

            required_fields = ["best_bid", "best_ask"]
            if atomic_ops:
                market_data = await atomic_ops.safe_market_data_read(market_key, required_fields=required_fields)
            else:
                market_data = await redis.hgetall(market_key)

            if not market_data:
                raise DataError(f"USDC pair market data not available for {currency}; key '{market_key}' missing")

            else:
                return market_data
        except RedisDataValidationError as exc:
            logger.debug("USDC market data not available for %s: %s", currency, exc)
            raise
        except REDIS_ERRORS as exc:
            logger.error("Error getting USDC market data for %s: %s", currency, exc, exc_info=True)
            raise
