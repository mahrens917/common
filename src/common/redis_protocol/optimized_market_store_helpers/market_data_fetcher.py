"""
Market data fetching for OptimizedMarketStore - slim coordinator.
"""

import logging
from typing import TYPE_CHECKING, Dict, Optional

from common.exceptions import DataError

from .market_data_fetcher_helpers import MarketKeyBuilder, PayloadConverter

if TYPE_CHECKING:
    from ...data_models.instrument import Instrument

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    """
    Fetches market data for instruments from Redis.

    Slim coordinator delegating to key builder and payload converter.
    """

    def __init__(self, redis_getter):
        """
        Initialize market data fetcher.

        Args:
            redis_getter: Async function that returns Redis client
        """
        self._get_redis = redis_getter
        self._key_builder = MarketKeyBuilder()
        self._payload_converter = PayloadConverter()

    def _format_key(
        self,
        currency: str,
        expiry: str,
        strike: Optional[float] = None,
        option_type: Optional[str] = None,
    ) -> str:
        """
        Format Redis key for instrument (delegates to key builder).

        Args:
            currency: Currency symbol (e.g., BTC, ETH)
            expiry: Expiry date in Deribit format (e.g., 28FEB25)
            strike: Strike price (None for futures)
            option_type: Option type (C or P, None for futures)

        Returns:
            Redis key for the instrument
        """
        return self._key_builder.format_key(currency, expiry, strike, option_type)

    async def get_market_data(self, instrument: "Instrument", original_key: Optional[str] = None) -> Dict:
        """
        Fetch market data for an instrument without caching.

        Args:
            instrument: Instrument to fetch data for
            original_key: Optional pre-computed Redis key

        Returns:
            Market data dictionary

        Raises:
            ValueError: When the key cannot be derived or the payload is incomplete.
        """
        key = self._determine_market_key(instrument, original_key)
        logger.debug("Querying Redis with key: %s", key)

        redis_client = await self._get_redis()
        data = await redis_client.hgetall(key)

        if not data:
            raise DataError(f"No Deribit market data found for key: {key}")

        payload = self._convert_market_payload(data)
        if payload.get("best_bid") is None or payload.get("best_ask") is None:
            raise DataError(f"Market data at key '{key}' missing best bid/ask fields")

        return payload

    def _determine_market_key(self, instrument: "Instrument", original_key: Optional[str]) -> str:
        """Determine market key (delegates to key builder)."""
        return self._key_builder.determine_market_key(instrument, original_key)

    def _convert_market_payload(self, raw: Dict) -> Dict:
        """Convert market payload (delegates to payload converter)."""
        return self._payload_converter.convert_market_payload(raw)
