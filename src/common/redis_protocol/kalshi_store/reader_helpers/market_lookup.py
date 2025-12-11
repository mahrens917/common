"""
Market Lookup - Market data lookup operations

Handles market data retrieval for specific strike/expiry combinations.
"""

import logging
from typing import Any, Dict, List, Optional

from redis.asyncio import Redis

from .market_record_builder import build_market_records
from .strike_matcher import find_matching_market

logger = logging.getLogger(__name__)


class MarketLookup:
    """Look up market data by strike/expiry combinations"""

    def __init__(
        self,
        logger_instance: logging.Logger,
        metadata_extractor,
        orderbook_reader,
        ticker_parser,
    ):
        self.logger = logger_instance
        self._metadata_extractor = metadata_extractor
        self._orderbook_reader = orderbook_reader
        self._ticker_parser = ticker_parser

    async def get_markets_by_currency(
        self,
        redis: Redis,
        currency: str,
        market_filter,
        get_market_key_func,
    ) -> List[Dict]:
        market_tickers = await market_filter.find_currency_market_tickers(redis, currency, self._ticker_parser.is_market_for_currency)
        if not market_tickers:
            self.logger.warning("No Kalshi market data found for %s in Redis", currency)
            return []

        results, skip_reasons = await build_market_records(
            redis=redis,
            market_tickers=market_tickers,
            currency=currency,
            ticker_parser=self._ticker_parser,
            metadata_extractor=self._metadata_extractor,
            get_market_key_func=get_market_key_func,
            logger_instance=self.logger,
        )

        market_filter.log_market_summary(
            currency=currency,
            total=len(market_tickers),
            processed=len(results),
            skip_reasons=skip_reasons,
        )
        return results

    async def get_market_data_for_strike_expiry(
        self,
        redis: Redis,
        currency: str,
        expiry: str,
        strike: float,
        markets: Any,
        get_market_key_func,
    ) -> Optional[Dict]:
        from .strike_matcher import MarketMatcherDependencies

        deps = MarketMatcherDependencies(
            redis=redis,
            currency=currency,
            expiry=expiry,
            strike=strike,
            markets=markets,
            get_market_key_func=get_market_key_func,
            ticker_parser=self._ticker_parser,
            metadata_extractor=self._metadata_extractor,
            orderbook_reader=self._orderbook_reader,
        )
        return await find_matching_market(deps)
