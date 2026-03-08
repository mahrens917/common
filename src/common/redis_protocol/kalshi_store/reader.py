from __future__ import annotations

"""
Kalshi Market Reader - Read-only operations for Kalshi market data

This module provides read-only access to Kalshi market data stored in Redis.
Extracted from KalshiStore to reduce class size and improve separation of concerns.
"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from common.config.redis_schema import RedisSchemaConfig
from common.parsing_utils import decode_redis_key
from common.redis_schema import build_kalshi_market_key

SCHEMA = RedisSchemaConfig.load()

from .connection import RedisConnectionManager
from .metadata import KalshiMetadataAdapter
from .reader_async_methods_mixin import KalshiMarketReaderAsyncMethodsMixin
from .reader_helpers import ReaderConnectionWrapper, dependencies_factory
from .reader_helpers.dependencies_factory import (
    KalshiMarketReaderDependencies,
)
from .reader_helpers.market_query_handler import MarketQueryHandler
from .reader_helpers.market_status_checker import MarketStatusChecker
from .reader_helpers.snapshot_retriever import SnapshotRetriever

logger = logging.getLogger(__name__)


class KalshiMarketReader(KalshiMarketReaderAsyncMethodsMixin):
    """Read-only operations for Kalshi market data in Redis"""

    SUBSCRIPTIONS_KEY: str = "kalshi:subscriptions"

    def __init__(
        self,
        connection_manager: RedisConnectionManager,
        logger: logging.Logger,
        metadata_adapter: KalshiMetadataAdapter,
        service_prefix: Optional[str] = None,
        *,
        subscriptions_key: Optional[str] = None,
        dependencies: Optional[KalshiMarketReaderDependencies] = None,
    ) -> None:
        self._conn, self.logger, self._metadata, self.service_prefix = (
            ReaderConnectionWrapper(connection_manager, logger),
            logger,
            metadata_adapter,
            service_prefix,
        )
        deps = dependencies or dependencies_factory.create_dependencies(logger, metadata_adapter)
        self._ticker_parser = deps.ticker_parser
        self._market_filter = deps.market_filter
        self._metadata_extractor = deps.metadata_extractor
        self._orderbook_reader = deps.orderbook_reader
        self._market_aggregator = deps.market_aggregator
        self._expiry_checker = deps.expiry_checker
        self._snapshot_reader = deps.snapshot_reader
        self._market_lookup = deps.market_lookup

        self._status_checker = MarketStatusChecker(self._conn, self._ticker_parser, self._expiry_checker, self.get_market_key)
        self._snapshot_retriever = SnapshotRetriever(self._conn, self._snapshot_reader, self.get_market_key)
        self._query_handler = MarketQueryHandler(
            self._conn,
            self._market_lookup,
            self._market_filter,
            self._market_aggregator,
            self._snapshot_reader,
            logger,
            self.get_market_key,
        )
        if subscriptions_key:
            self.SUBSCRIPTIONS_KEY = subscriptions_key

    def get_market_key(self, market_ticker: str) -> str:
        return build_kalshi_market_key(market_ticker)

    def is_market_for_currency(self, market_ticker: str, currency: str) -> bool:
        return self._ticker_parser.is_market_for_currency(market_ticker, currency)

    def aggregate_markets_by_point(
        self, markets: Sequence[Dict[str, Any]]
    ) -> Tuple[Dict[Tuple[str, float, str], List[str]], Dict[str, Dict[str, Any]]]:
        return self._market_aggregator.aggregate_markets_by_point(markets)

    def build_strike_summary(
        self,
        grouped: Dict[Tuple[str, float, str], List[str]],
        market_by_ticker: Dict[str, Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        return self._market_aggregator.build_strike_summary(grouped, market_by_ticker)

    def ensure_market_metadata_fields(self, ticker: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        return self._metadata.ensure_market_metadata_fields(ticker, snapshot)

    async def get_subscribed_markets(self) -> Set[str]:
        return await self._query_handler.get_subscribed_markets(self.SUBSCRIPTIONS_KEY)

    async def is_market_tracked(self, market_ticker: str) -> bool:
        return await self._query_handler.is_tracked(market_ticker)

    async def get_markets_by_currency(self, currency: str) -> List[Dict[str, Any]]:
        return await self._query_handler.get_by_currency(currency)

    async def get_all_markets(self) -> List[Dict[str, Any]]:
        return await self._query_handler.get_all()

    async def get_active_strikes_and_expiries(self, currency: str) -> Dict[str, List[Dict[str, Any]]]:
        return await self._query_handler.get_strikes_and_expiries(currency)

    async def get_market_data_for_strike_expiry(self, currency: str, expiry: str, strike: float) -> Optional[Dict[str, Any]]:
        return await self._query_handler.get_for_strike_expiry(currency, expiry, strike, self.SUBSCRIPTIONS_KEY)

    async def is_market_expired(
        self,
        market_ticker: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return await self._status_checker.is_expired(market_ticker, metadata=metadata)

    async def is_market_settled(self, market_ticker: str) -> bool:
        return await self._status_checker.is_settled(market_ticker)

    async def get_market_snapshot(self, ticker: str, *, include_orderbook: bool = True) -> Dict[str, Any]:
        return await self._snapshot_retriever.get_snapshot(ticker, include_orderbook=include_orderbook)

    async def get_market_snapshot_by_key(self, market_key: str, *, include_orderbook: bool = True) -> Dict[str, Any]:
        return await self._snapshot_retriever.get_snapshot_by_key(market_key, include_orderbook=include_orderbook)

    async def get_market_metadata(self, ticker: str) -> Dict[str, Any]:
        return await self._snapshot_retriever.get_metadata(ticker)

    async def get_market_field(self, ticker: str, field: str, fill_value: Optional[str] = None) -> str:
        try:
            return await self._snapshot_retriever.get_field(ticker, field)
        except (KeyError, ValueError, TypeError, RuntimeError):
            if fill_value is not None:
                return fill_value
            raise

    async def get_orderbook(self, ticker: str) -> Dict[str, Any]:
        if not await self._conn.ensure_connection():
            return {}
        redis = await self._conn.get_redis()
        return await self._orderbook_reader.get_orderbook(redis, self.get_market_key(ticker), ticker)

    async def get_orderbook_side(self, ticker: str, side: str) -> Dict[str, Any]:
        if not await self._conn.ensure_connection():
            return {}
        redis = await self._conn.get_redis()
        return await self._orderbook_reader.get_orderbook_side(redis, self.get_market_key(ticker), ticker, side)

    async def scan_market_keys(self, patterns: Optional[List[str]] = None) -> List[str]:
        if not await self._conn.ensure_connection():
            raise RuntimeError("Redis connection not established for scan_market_keys")
        redis = await self._conn.get_redis()
        target_patterns = patterns
        if not target_patterns:
            target_patterns = list()
            target_patterns.append(f"{SCHEMA.kalshi_market_prefix}:*")
        seen: Set[str] = set()
        results: List[str] = []
        for pattern in target_patterns:
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor, match=pattern, count=1000)
                for raw_key in keys:
                    key_str = decode_redis_key(raw_key)
                    if key_str not in seen:
                        seen.add(key_str)
                        results.append(key_str)
                if cursor == 0:
                    break
        return results
