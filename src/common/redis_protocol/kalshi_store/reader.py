from __future__ import annotations

"""
Kalshi Market Reader - Read-only operations for Kalshi market data

This module provides read-only access to Kalshi market data stored in Redis.
Extracted from KalshiStore to reduce class size and improve separation of concerns.
"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from src.common.config.redis_schema import get_schema_config
from src.common.parsing_utils import decode_redis_key
from src.common.redis_schema import build_kalshi_market_key

SCHEMA = get_schema_config()

from .connection import RedisConnectionManager
from .metadata import KalshiMetadataAdapter
from .reader_async_methods_mixin import KalshiMarketReaderAsyncMethodsMixin
from .reader_helpers import ReaderConnectionWrapper
from .reader_helpers.dependencies_factory import (
    KalshiMarketReaderDependencies,
    KalshiMarketReaderDependenciesFactory,
)
from .reader_helpers.expiry_checker import ExpiryChecker
from .reader_helpers.market_aggregator import MarketAggregator
from .reader_helpers.market_filter import MarketFilter
from .reader_helpers.market_lookup import MarketLookup
from .reader_helpers.market_query_handler import MarketQueryHandler
from .reader_helpers.market_status_checker import MarketStatusChecker
from .reader_helpers.snapshot_reader import SnapshotReader
from .reader_helpers.snapshot_retriever import SnapshotRetriever
from .reader_helpers.snapshotreader_helpers import KalshiStoreError
from .reader_helpers.ticker_parser import TickerParser

logger = logging.getLogger(__name__)


async def _get_subscribed_markets(store: "KalshiMarketReader") -> Set[str]:
    query_handler = getattr(store, "_query_handler")
    return await query_handler.get_subscribed_markets(store.SUBSCRIPTIONS_KEY)


async def _is_market_tracked(store: "KalshiMarketReader", market_ticker: str) -> bool:
    query_handler = getattr(store, "_query_handler")
    return await query_handler.is_tracked(market_ticker)


async def _get_markets_by_currency(
    store: "KalshiMarketReader", currency: str
) -> List[Dict[str, Any]]:
    query_handler = getattr(store, "_query_handler")
    return await query_handler.get_by_currency(currency)


async def _get_active_strikes_and_expiries(
    store: "KalshiMarketReader", currency: str
) -> Dict[str, List[Dict[str, Any]]]:
    query_handler = getattr(store, "_query_handler")
    return await query_handler.get_strikes_and_expiries(currency)


async def _get_market_data_for_strike_expiry(
    store: "KalshiMarketReader", currency: str, expiry: str, strike: float
) -> Optional[Dict[str, Any]]:
    query_handler = getattr(store, "_query_handler")
    return await query_handler.get_for_strike_expiry(
        currency, expiry, strike, store.SUBSCRIPTIONS_KEY
    )


async def _is_market_expired(
    store: "KalshiMarketReader",
    market_ticker: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    status_checker = getattr(store, "_status_checker")
    return await status_checker.is_expired(market_ticker, metadata=metadata)


async def _is_market_settled(store: "KalshiMarketReader", market_ticker: str) -> bool:
    status_checker = getattr(store, "_status_checker")
    return await status_checker.is_settled(market_ticker)


async def _get_market_snapshot(
    store: "KalshiMarketReader", ticker: str, *, include_orderbook: bool = True
) -> Dict[str, Any]:
    snapshot_retriever = getattr(store, "_snapshot_retriever")
    return await snapshot_retriever.get_snapshot(ticker, include_orderbook=include_orderbook)


async def _get_market_snapshot_by_key(
    store: "KalshiMarketReader", market_key: str, *, include_orderbook: bool = True
) -> Dict[str, Any]:
    snapshot_retriever = getattr(store, "_snapshot_retriever")
    return await snapshot_retriever.get_snapshot_by_key(
        market_key, include_orderbook=include_orderbook
    )


async def _get_market_metadata(store: "KalshiMarketReader", ticker: str) -> Dict[str, Any]:
    snapshot_retriever = getattr(store, "_snapshot_retriever")
    return await snapshot_retriever.get_metadata(ticker)


async def _get_market_field(
    store: "KalshiMarketReader", ticker: str, field: str, default: Optional[str] = None
) -> str:
    snapshot_retriever = getattr(store, "_snapshot_retriever")
    try:
        return await snapshot_retriever.get_field(ticker, field)
    except (KeyError, ValueError, TypeError, RuntimeError):
        if default is not None:
            return default
        raise


async def _get_orderbook(store: "KalshiMarketReader", ticker: str) -> Dict[str, Any]:
    conn = getattr(store, "_conn")
    if not await conn.ensure_connection():
        return {}
    redis = await conn.get_redis()
    orderbook_reader = getattr(store, "_orderbook_reader")
    return await orderbook_reader.get_orderbook(redis, store.get_market_key(ticker), ticker)


async def _get_orderbook_side(
    store: "KalshiMarketReader", ticker: str, side: str
) -> Dict[str, Any]:
    conn = getattr(store, "_conn")
    if not await conn.ensure_connection():
        return {}
    redis = await conn.get_redis()
    orderbook_reader = getattr(store, "_orderbook_reader")
    return await orderbook_reader.get_orderbook_side(
        redis, store.get_market_key(ticker), ticker, side
    )


async def _scan_market_keys(
    store: "KalshiMarketReader", patterns: Optional[List[str]] = None
) -> List[str]:
    conn = getattr(store, "_conn")
    if not await conn.ensure_connection():
        raise RuntimeError("Redis connection not established for scan_market_keys")
    redis = await conn.get_redis()
    target_patterns = patterns or [f"{SCHEMA.kalshi_market_prefix}:*"]
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
        deps = dependencies or KalshiMarketReaderDependenciesFactory.create(
            logger, metadata_adapter
        )
        self._ticker_parser = deps.ticker_parser
        self._market_filter = deps.market_filter
        self._metadata_extractor = deps.metadata_extractor
        self._orderbook_reader = deps.orderbook_reader
        self._market_aggregator = deps.market_aggregator
        self._expiry_checker = deps.expiry_checker
        self._snapshot_reader = deps.snapshot_reader
        self._market_lookup = deps.market_lookup

        self._status_checker = MarketStatusChecker(
            self._conn, self._ticker_parser, self._expiry_checker, self.get_market_key
        )
        self._snapshot_retriever = SnapshotRetriever(
            self._conn, self._snapshot_reader, self.get_market_key
        )
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

    def ensure_market_metadata_fields(
        self, ticker: str, snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self._metadata.ensure_market_metadata_fields(ticker, snapshot)


def _make_async_wrapper(helper):
    async def wrapper(self, *args, **kwargs):
        return await helper(self, *args, **kwargs)

    wrapper.__doc__ = helper.__doc__
    return wrapper


_ASYNC_HELPERS = [
    ("get_subscribed_markets", _get_subscribed_markets),
    ("is_market_tracked", _is_market_tracked),
    ("get_markets_by_currency", _get_markets_by_currency),
    ("get_active_strikes_and_expiries", _get_active_strikes_and_expiries),
    ("get_market_data_for_strike_expiry", _get_market_data_for_strike_expiry),
    ("is_market_expired", _is_market_expired),
    ("is_market_settled", _is_market_settled),
    ("get_market_snapshot", _get_market_snapshot),
    ("get_market_snapshot_by_key", _get_market_snapshot_by_key),
    ("get_market_metadata", _get_market_metadata),
    ("get_market_field", _get_market_field),
    ("get_orderbook", _get_orderbook),
    ("get_orderbook_side", _get_orderbook_side),
    ("scan_market_keys", _scan_market_keys),
]

for name, helper in _ASYNC_HELPERS:
    setattr(KalshiMarketReader, name, _make_async_wrapper(helper))
