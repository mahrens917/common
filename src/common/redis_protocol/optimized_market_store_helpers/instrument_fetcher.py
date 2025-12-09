"""
Instrument fetching for OptimizedMarketStore - slim coordinator.
"""

import logging
from typing import List

from ..error_types import REDIS_ERRORS
from .instrument_fetcher_helpers import InstrumentBuilder, RedisInstrumentScanner

logger = logging.getLogger(__name__)


class InstrumentFetcher:
    """
    Fetches instruments from Redis.

    Slim coordinator delegating to scanner and builder.
    """

    def __init__(self, redis_getter):
        """
        Initialize instrument fetcher.

        Args:
            redis_getter: Async function that returns Redis client
        """
        self._get_redis = redis_getter
        self._scanner = RedisInstrumentScanner(redis_getter)
        self._builder = InstrumentBuilder()

    async def get_all_instruments(self, currency: str) -> List:
        """Return instruments for a currency using the unified Redis schema."""
        try:
            scan_results = await self._scanner.scan_and_fetch_instruments(currency)
            instruments = self._builder.build_instruments(scan_results)

            logger.info(
                "KEY_SCAN_DEBUG: Returning %s instruments for currency %s",
                len(instruments),
                currency,
            )

        except REDIS_ERRORS as exc:
            logger.error("Error in get_all_instruments for %s: %s", currency, exc, exc_info=True)
            return []
        else:
            return instruments

    async def get_options_by_currency(self, currency: str) -> List:
        """Return all option instruments for a currency."""
        try:
            instruments = await self.get_all_instruments(currency)
            return [instrument for instrument in instruments if not instrument.is_future]
        except REDIS_ERRORS as exc:
            logger.error(
                "Error in get_options_by_currency for %s: %s", currency, exc, exc_info=True
            )
            return []

    async def get_futures_by_currency(self, currency: str) -> List:
        """Return all future instruments for a currency."""
        try:
            instruments = await self.get_all_instruments(currency)
            return [instrument for instrument in instruments if instrument.is_future]
        except REDIS_ERRORS as exc:
            logger.error(
                "Error in get_futures_by_currency for %s: %s", currency, exc, exc_info=True
            )
            return []

    async def get_puts_by_currency(self, currency: str) -> List:
        """Return all put option instruments for a currency."""
        try:
            instruments = await self.get_all_instruments(currency)
            return [
                instrument
                for instrument in instruments
                if not instrument.is_future and instrument.option_type == "put"
            ]
        except REDIS_ERRORS as exc:
            logger.error("Error in get_puts_by_currency for %s: %s", currency, exc, exc_info=True)
            return []
