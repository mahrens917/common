"""Tests for Kalshi store reader helpers."""

import logging
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.redis_protocol.kalshi_store.reader import (
    KalshiMarketReader,
    MarketQueryHandler,
    MarketStatusChecker,
    SnapshotRetriever,
)
from src.common.redis_protocol.kalshi_store.reader_helpers import (
    dependencies_factory,
)
from src.common.redis_protocol.kalshi_store.reader_helpers.connection_wrapper import (
    ReaderConnectionWrapper,
)
from src.common.redis_protocol.kalshi_store.reader_helpers.dependencies_factory import (
    KalshiMarketReaderDependencies,
)
from src.common.redis_protocol.kalshi_store.reader_helpers.snapshotreader_helpers import (
    KalshiStoreError,
)
from src.common.redis_schema import build_kalshi_market_key

LOGGER = logging.getLogger(__name__)


class DummyConnectionManager:
    def __init__(self, ensure: bool = True, redis: Any = None) -> None:
        self._ensure = ensure
        self._redis = redis or MagicMock(name="redis")

    async def ensure_connection(self) -> bool:
        return self._ensure

    async def get_redis(self):
        if isinstance(self._redis, Exception):
            raise self._redis
        return self._redis


def _connection_wrapper(ensure: bool = True, redis: Any = None) -> ReaderConnectionWrapper:
    return ReaderConnectionWrapper(DummyConnectionManager(ensure=ensure, redis=redis), LOGGER)


class DummyTickerParser:
    def __init__(self) -> None:
        self.normalized: List[str] = []

    def normalize_ticker(self, ticker: str) -> str:
        normalized = ticker.lower()
        self.normalized.append(normalized)
        return normalized

    def is_market_for_currency(self, market_ticker: str, currency: str) -> bool:
        return currency.lower() in market_ticker.lower()


class DummyExpiryChecker:
    def __init__(self, expired: bool = False, settled: bool = False) -> None:
        self.expired = expired
        self.settled = settled

    async def is_market_expired(self, *args: Any, **kwargs: Any) -> bool:
        return self.expired

    async def is_market_settled(self, *args: Any, **kwargs: Any) -> bool:
        return self.settled


class DummySnapshotReader:
    def __init__(self, subscribed: Optional[Set[str]] = None) -> None:
        self.subscribed = subscribed if subscribed is not None else {"KXHIGHTEST"}

    async def get_market_snapshot(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {"ticker": args[2], "include_orderbook": kwargs.get("include_orderbook", True)}

    async def get_market_metadata(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {"meta": "value"}

    async def get_market_field(self, *args: Any, **kwargs: Any) -> str:
        return "field"

    async def get_subscribed_markets(self, *args: Any, **kwargs: Any) -> Set[str]:
        return self.subscribed

    async def is_market_tracked(self, *args: Any, **kwargs: Any) -> bool:
        return True


class DummyOrderbookReader:
    async def get_orderbook(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {"orderbook": True, "key": args[1], "ticker": args[2]}

    async def get_orderbook_side(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {"orderbook_side": args[3], "side": kwargs.get("side")}


class DummyMarketFilter:
    pass


class DummyMarketLookup:
    def __init__(
        self,
        markets: Optional[List[Dict[str, Any]]] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.markets = markets or []
        self.market_data = market_data or {"found": True}

    async def get_markets_by_currency(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        return self.markets

    async def get_market_data_for_strike_expiry(
        self, *args: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        return self.market_data


class DummyMarketAggregator:
    def aggregate_markets_by_point(
        self, markets: List[Dict[str, Any]]
    ) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        grouped = {"points": [market["ticker"] for market in markets]}
        summary = {market["ticker"]: market for market in markets}
        return grouped, summary

    def build_strike_summary(
        self, grouped: Dict[str, Any], market_by_ticker: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        return {"summary": list(market_by_ticker)}


class DummyMetadataAdapter:
    def ensure_market_metadata_fields(
        self, _telemetry: str, snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        return snapshot


class DummyDependencies:
    def __init__(self) -> None:
        self.ticker_parser = DummyTickerParser()
        self.market_filter = DummyMarketFilter()
        self.metadata_extractor = MagicMock()
        self.orderbook_reader = MagicMock()
        self.market_aggregator = DummyMarketAggregator()
        self.expiry_checker = DummyExpiryChecker()
        self.snapshot_reader = DummySnapshotReader()
        self.market_lookup = DummyMarketLookup()


@pytest.mark.asyncio
async def test_market_status_checker_returns_false_without_connection():
    checker = MarketStatusChecker(
        _connection_wrapper(ensure=False),
        DummyTickerParser(),
        DummyExpiryChecker(expired=True),
        lambda ticker: f"key:{ticker}",
    )

    assert await checker.is_expired("KXHIGHTEST") is False


@pytest.mark.asyncio
async def test_market_status_checker_queries_expiry_when_connected():
    ticker_parser = DummyTickerParser()
    expiry_checker = DummyExpiryChecker(expired=True)
    checker = MarketStatusChecker(
        _connection_wrapper(),
        ticker_parser,
        expiry_checker,
        lambda ticker: f"key:{ticker}",
    )

    assert await checker.is_expired("KXHIGHTEST")
    assert ticker_parser.normalized[-1] == "kxhightest"


@pytest.mark.asyncio
async def test_snapshot_retriever_handles_redis_error():
    retriever = SnapshotRetriever(
        _connection_wrapper(redis=RuntimeError("boom")),
        DummySnapshotReader(),
        lambda ticker: build_kalshi_market_key(ticker),
    )

    with pytest.raises(KalshiStoreError):
        await retriever.get_snapshot("KXHIGHTEST")


@pytest.mark.asyncio
async def test_snapshot_retriever_get_snapshot_by_key_rejects_empty_market_key():
    retriever = SnapshotRetriever(
        _connection_wrapper(),
        DummySnapshotReader(),
        lambda ticker: build_kalshi_market_key(ticker),
    )

    with pytest.raises(TypeError):
        await retriever.get_snapshot_by_key("")


@pytest.mark.asyncio
async def test_snapshot_retriever_get_snapshot_by_key_returns_data():
    reader = DummySnapshotReader()
    retriever = SnapshotRetriever(
        _connection_wrapper(),
        reader,
        lambda ticker: build_kalshi_market_key(ticker),
    )

    snapshot = await retriever.get_snapshot_by_key(build_kalshi_market_key("KXHIGHTEST"))

    assert snapshot["ticker"].lower() == "kxhightest"


@pytest.mark.asyncio
async def test_snapshot_retriever_get_field_returns_empty_when_disconnected():
    retriever = SnapshotRetriever(
        _connection_wrapper(ensure=False),
        DummySnapshotReader(),
        lambda ticker: build_kalshi_market_key(ticker),
    )

    assert await retriever.get_field("KXHIGHTEST", "status") == ""


@pytest.mark.asyncio
async def test_market_query_handler_errors_when_no_markets_found():
    handler = MarketQueryHandler(
        _connection_wrapper(),
        DummyMarketLookup(markets=[]),
        DummyMarketFilter(),
        DummyMarketAggregator(),
        DummySnapshotReader(),
        LOGGER,
        lambda ticker: build_kalshi_market_key(ticker),
    )

    with pytest.raises(KalshiStoreError):
        await handler.get_strikes_and_expiries("USD")


@pytest.mark.asyncio
async def test_market_query_handler_returns_summary():
    handler = MarketQueryHandler(
        _connection_wrapper(),
        DummyMarketLookup(markets=[{"ticker": "KXHIGHTEST"}]),
        DummyMarketFilter(),
        DummyMarketAggregator(),
        DummySnapshotReader(),
        LOGGER,
        lambda ticker: build_kalshi_market_key(ticker),
    )

    result = await handler.get_strikes_and_expiries("USD")

    assert result == {"summary": ["KXHIGHTEST"]}


@pytest.mark.asyncio
async def test_market_query_handler_returns_none_when_connection_fails():
    handler = MarketQueryHandler(
        _connection_wrapper(ensure=False),
        DummyMarketLookup(markets=[{"ticker": "KXHIGHTEST"}]),
        DummyMarketFilter(),
        DummyMarketAggregator(),
        DummySnapshotReader(),
        LOGGER,
        lambda ticker: build_kalshi_market_key(ticker),
    )

    assert await handler.get_for_strike_expiry("USD", "expiry", 1.0, "subs") is None


@pytest.mark.asyncio
async def test_market_query_handler_returns_none_when_no_subscriptions():
    handler = MarketQueryHandler(
        _connection_wrapper(),
        DummyMarketLookup(markets=[{"ticker": "KXHIGHTEST"}]),
        DummyMarketFilter(),
        DummyMarketAggregator(),
        DummySnapshotReader(subscribed=set()),
        LOGGER,
        lambda ticker: build_kalshi_market_key(ticker),
    )

    assert await handler.get_for_strike_expiry("USD", "expiry", 1.0, "subs") is None


@pytest.mark.asyncio
async def test_market_query_handler_returns_market_data_when_available():
    handler = MarketQueryHandler(
        _connection_wrapper(),
        DummyMarketLookup(
            markets=[{"ticker": "KXHIGHTEST"}],
            market_data={"ticker": "KXHIGHTEST", "value": 1},
        ),
        DummyMarketFilter(),
        DummyMarketAggregator(),
        DummySnapshotReader(subscribed={"KXHIGHTEST"}),
        LOGGER,
        lambda ticker: build_kalshi_market_key(ticker),
    )

    assert await handler.get_for_strike_expiry("USD", "expiry", 1.0, "subs") == {
        "ticker": "KXHIGHTEST",
        "value": 1,
    }


@pytest.mark.asyncio
async def test_kalshi_market_reader_get_field_returns_default(monkeypatch):
    dependencies = DummyDependencies()
    monkeypatch.setattr(
        dependencies_factory.KalshiMarketReaderDependenciesFactory,
        "create",
        lambda logger, metadata_adapter: dependencies,
    )

    reader = KalshiMarketReader(DummyConnectionManager(), LOGGER, DummyMetadataAdapter())
    reader._snapshot_retriever = MagicMock()
    reader._snapshot_retriever.get_field = AsyncMock(side_effect=RuntimeError("boom"))

    assert await reader.get_market_field("KXHIGHTEST", "status", default="fallback") == "fallback"


@pytest.mark.asyncio
async def test_kalshi_market_reader_snapshot_and_orderbook_paths(monkeypatch):
    dependencies = KalshiMarketReaderDependencies(
        ticker_parser=DummyTickerParser(),
        market_filter=DummyMarketFilter(),
        metadata_extractor=MagicMock(),
        orderbook_reader=DummyOrderbookReader(),
        market_aggregator=DummyMarketAggregator(),
        expiry_checker=DummyExpiryChecker(),
        snapshot_reader=DummySnapshotReader(),
        market_lookup=DummyMarketLookup(),
    )
    reader = KalshiMarketReader(
        DummyConnectionManager(),
        LOGGER,
        DummyMetadataAdapter(),
        dependencies=dependencies,
    )

    snapshot = await reader.get_market_snapshot("KXHIGHTEST")
    assert snapshot["ticker"] == "KXHIGHTEST"
    assert await reader.get_market_metadata("KXHIGHTEST") == {"meta": "value"}

    redis_mgr = DummyConnectionManager(ensure=False)
    reader_no_conn = KalshiMarketReader(
        redis_mgr, LOGGER, DummyMetadataAdapter(), dependencies=dependencies
    )
    assert await reader_no_conn.get_orderbook("KXHIGHTEST") == {}
    assert await reader_no_conn.get_orderbook_side("KXHIGHTEST", "yes") == {}


@pytest.mark.asyncio
async def test_kalshi_market_reader_query_paths(monkeypatch):
    dependencies = DummyDependencies()
    reader = KalshiMarketReader(
        DummyConnectionManager(),
        LOGGER,
        DummyMetadataAdapter(),
        dependencies=KalshiMarketReaderDependencies(
            ticker_parser=dependencies.ticker_parser,
            market_filter=dependencies.market_filter,
            metadata_extractor=dependencies.metadata_extractor,
            orderbook_reader=dependencies.orderbook_reader,
            market_aggregator=dependencies.market_aggregator,
            expiry_checker=dependencies.expiry_checker,
            snapshot_reader=dependencies.snapshot_reader,
            market_lookup=dependencies.market_lookup,
        ),
    )

    class QueryStub:
        async def get_by_currency(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
            return [{"ticker": "KXHIGHTEST"}]

        async def get_strikes_and_expiries(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"grouped": []}

        async def get_for_strike_expiry(
            self, *args: Any, **kwargs: Any
        ) -> Optional[Dict[str, Any]]:
            return {"value": 1}

        async def get_subscribed_markets(self, *args: Any, **kwargs: Any) -> Set[str]:
            return {"KXHIGHTEST"}

        async def is_tracked(self, *args: Any, **kwargs: Any) -> bool:
            return True

    reader._query_handler = QueryStub()
    reader._snapshot_reader = dependencies.snapshot_reader

    assert await reader.get_markets_by_currency("USD") == [{"ticker": "KXHIGHTEST"}]
    assert await reader.get_active_strikes_and_expiries("USD") == {"grouped": []}
    assert await reader.get_market_data_for_strike_expiry("USD", "expiry", 5.0) == {"value": 1}
    assert await reader.get_subscribed_markets() == {"KXHIGHTEST"}
    assert await reader.is_market_tracked("KXHIGHTEST")
