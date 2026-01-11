"""Market query handling helper for KalshiMarketReader."""

import logging
from typing import Dict, List, Optional, Set

from .market_aggregator import MarketAggregator
from .market_filter import MarketFilter
from .market_lookup import MarketLookup
from .snapshot_reader import SnapshotReader
from .snapshotreader_helpers import KalshiStoreError


class MarketQueryHandler:
    """Handles complex market queries."""

    def __init__(
        self,
        conn_wrapper,
        market_lookup: MarketLookup,
        market_filter: MarketFilter,
        market_aggregator: MarketAggregator,
        snapshot_reader: SnapshotReader,
        query_logger: logging.Logger,
        get_key_fn,
    ):
        self._conn = conn_wrapper
        self._market_lookup = market_lookup
        self._market_filter = market_filter
        self._market_aggregator = market_aggregator
        self._snapshot_reader = snapshot_reader
        self._logger = query_logger
        self._get_key = get_key_fn

    async def get_subscribed_markets(self, subscriptions_key: str) -> Set[str]:
        """Get set of subscribed markets."""
        redis = await self._conn.ensure_or_raise("get_subscribed_markets")
        return await self._snapshot_reader.get_subscribed_markets(redis, subscriptions_key)

    async def is_tracked(self, market_ticker: str) -> bool:
        """Check if market is tracked."""
        if not await self._conn.ensure_connection():
            raise RuntimeError(f"Failed to ensure Redis for is_market_tracked {market_ticker}")
        redis = await self._conn.get_redis()
        return await self._snapshot_reader.is_market_tracked(redis, self._get_key(market_ticker), market_ticker)

    async def get_by_currency(self, currency: str) -> List[Dict]:
        """Get markets by currency."""
        redis = await self._conn.ensure_or_raise(f"get_markets_by_currency {currency}")
        return await self._market_lookup.get_markets_by_currency(redis, currency, self._market_filter, self._get_key)

    async def get_all(self) -> List[Dict]:
        """Get all markets."""
        redis = await self._conn.ensure_or_raise("get_all_markets")
        return await self._market_lookup.get_all_markets(redis, self._market_filter, self._get_key)

    async def get_strikes_and_expiries(self, currency: str) -> Dict[str, List[Dict]]:
        """Get active strikes and expiries for currency."""
        markets = await self.get_by_currency(currency)
        if not markets:
            raise KalshiStoreError(f"No active Kalshi markets found for currency {currency}")
        grouped, market_by_ticker = self._market_aggregator.aggregate_markets_by_point(markets)
        return self._market_aggregator.build_strike_summary(grouped, market_by_ticker)

    async def get_for_strike_expiry(self, currency: str, expiry: str, strike: float, subscriptions_key: str) -> Optional[Dict]:
        """Get market data for strike and expiry."""
        if not await self._conn.ensure_connection():
            self._logger.error("Failed to ensure Redis for get_market_data_for_strike_expiry")
            return None
        markets = await self.get_subscribed_markets(subscriptions_key)
        if not markets:
            return None
        redis = await self._conn.get_redis()
        return await self._market_lookup.get_market_data_for_strike_expiry(
            redis,
            currency,
            expiry,
            strike,
            markets,
            self._get_key,
        )
