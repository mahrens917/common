from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import AsyncMock

import pytest

from common.data_models.instrument import Instrument
from common.redis_protocol.optimized_market_store import OptimizedMarketStore
from common.redis_schema.markets import (
    DeribitInstrumentDescriptor,
    DeribitInstrumentKey,
    DeribitInstrumentType,
)

_TEST_COUNT_2 = 2
_TEST_COUNT_3 = 3
_VAL_101_5 = 101.5
_VAL_102_5 = 102.5
_VAL_5_0 = 5.0


class FakeRedis:
    def __init__(self, mapping: dict[str, dict[str, str]]):
        self.mapping = mapping

    async def hgetall(self, key: str):
        return self.mapping.get(key, {})


def make_store(redis_mapping: dict[str, dict[str, str]]):
    from common.redis_protocol.optimized_market_store_helpers.expiry_converter import (
        ExpiryConverter,
    )
    from common.redis_protocol.optimized_market_store_helpers.instrument_fetcher import (
        InstrumentFetcher,
    )
    from common.redis_protocol.optimized_market_store_helpers.market_data_fetcher import (
        MarketDataFetcher,
    )
    from common.redis_protocol.optimized_market_store_helpers.spot_price_fetcher import (
        SpotPriceFetcher,
    )

    store = OptimizedMarketStore.__new__(OptimizedMarketStore)
    store.redis = FakeRedis(redis_mapping)
    store.redis_pool = None
    store.initialized = True
    store.atomic_ops = None

    # Bind the actual _get_redis method from OptimizedMarketStore
    from types import MethodType

    # Get the _get_redis method from OptimizedMarketStore and bind it to the store instance
    store._get_redis = MethodType(OptimizedMarketStore._get_redis, store)

    store.expiry_converter = ExpiryConverter()
    store.market_data_fetcher = MarketDataFetcher(store._get_redis)
    store.instrument_fetcher = InstrumentFetcher(store._get_redis)
    store.spot_price_fetcher = SpotPriceFetcher(store._get_redis, None)
    return store


def _edge_case_keys() -> list[str]:
    return [
        "bad-key",
        "key-empty",
        "key-no-expiry",
        "key-bad-expiry",
        "key-valid",
        "key-bad-number",
    ]


def _edge_case_data_map() -> dict[str, dict[str, str]]:
    return {
        "key-empty": {},
        "key-no-expiry": {"best_bid": "1", "best_ask": "2"},
        "key-bad-expiry": {"best_bid": "1", "best_ask": "2"},
        "key-valid": {
            "best_bid": "1.5",
            "best_ask": "2.5",
            "best_bid_size": "3.1",
            "best_ask_size": "4.2",
            "implied_volatility": "0.5",
        },
        "key-bad-number": {"best_bid": "oops", "best_ask": "4.2"},
    }


def _edge_case_descriptor_map():
    return {
        "key-empty": SimpleNamespace(
            currency="BTC",
            expiry_iso="2025-02-28",
            strike=None,
            option_kind=None,
            instrument_type=DeribitInstrumentType.FUTURE,
        ),
        "key-no-expiry": SimpleNamespace(
            currency="BTC",
            expiry_iso=None,
            strike=None,
            option_kind=None,
            instrument_type=DeribitInstrumentType.FUTURE,
        ),
        "key-bad-expiry": SimpleNamespace(
            currency="BTC",
            expiry_iso="invalid",
            strike=None,
            option_kind=None,
            instrument_type=DeribitInstrumentType.FUTURE,
        ),
        "key-valid": SimpleNamespace(
            currency="BTC",
            expiry_iso="2025-02-28",
            strike="30000",
            option_kind="c",
            instrument_type=DeribitInstrumentType.OPTION,
        ),
        "key-bad-number": SimpleNamespace(
            currency="BTC",
            expiry_iso="2025-03-01",
            strike="35000",
            option_kind="p",
            instrument_type=DeribitInstrumentType.OPTION,
        ),
    }


class _PipelineStub:
    def __init__(self, mapping: dict[str, dict[str, str]]):
        self._mapping = mapping
        self._keys: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False

    def hgetall(self, key: str):
        self._keys.append(key)
        return self

    async def execute(self):
        return [self._mapping.get(key, {}) for key in self._keys]


class _RedisScanStub:
    def __init__(self, keys: list[str], mapping: dict[str, dict[str, str]]):
        self._keys = keys
        self._mapping = mapping

    async def scan(self, *args, **kwargs):
        return 0, self._keys

    def pipeline(self):
        return _PipelineStub(self._mapping)


def test_init_with_redis_instance_sets_pool(monkeypatch):
    class DummyRedis:
        def __init__(self):
            self.connection_pool = "pool"

        def hgetall(self): ...
        def hset(self): ...
        def pipeline(self): ...
        def publish(self): ...

    monkeypatch.setattr(
        "common.redis_protocol.optimized_market_store_helpers.redis_initializer.AtomicRedisOperations",
        lambda _redis: "atomic",
        raising=False,
    )

    store = OptimizedMarketStore(DummyRedis())

    assert store.redis_pool == "pool"
    assert store.atomic_ops == "atomic"


def test_is_redis_like_detection():
    from common.redis_protocol.optimized_market_store_helpers.redis_initializer import (
        RedisInitializer,
    )

    class RedisLike:
        def hgetall(self): ...

        def hset(self): ...

        def pipeline(self): ...

        def publish(self): ...

    assert RedisInitializer._is_redis_like(RedisLike())
    assert not RedisInitializer._is_redis_like(object())


def test_constructor_rejects_unknown_connection():
    with pytest.raises(TypeError):
        OptimizedMarketStore(object())


@pytest.mark.asyncio
async def test_get_redis_requires_initialization():
    store = OptimizedMarketStore.__new__(OptimizedMarketStore)
    store.redis = None
    store.initialized = False

    with pytest.raises(RuntimeError):
        await store._get_redis()


@pytest.mark.asyncio
async def test_create_initializes_from_connection_pool(monkeypatch):
    class DummyPool:
        pass

    class DummyRedis:
        def __init__(self, *, connection_pool=None, decode_responses=None):
            self.connection_pool = connection_pool
            self.decode_responses = decode_responses

        async def aclose(self):
            return None

    pool_instance = DummyPool()

    monkeypatch.setattr(
        "common.redis_protocol.optimized_market_store_helpers.redis_initializer.ConnectionPool",
        DummyPool,
        raising=False,
    )
    monkeypatch.setattr(
        "common.redis_protocol.optimized_market_store_helpers.redis_initializer.redis.asyncio.Redis",
        lambda *_, **kwargs: DummyRedis(**kwargs),
        raising=False,
    )
    monkeypatch.setattr(
        "common.redis_protocol.optimized_market_store_helpers.redis_initializer.get_redis_pool",
        AsyncMock(return_value=pool_instance),
        raising=False,
    )

    store = await OptimizedMarketStore.create()

    assert store.redis_pool is pool_instance
    assert isinstance(store.redis, DummyRedis)


def test_format_key_spot_and_option():
    from common.redis_protocol.optimized_market_store_helpers.market_data_fetcher_helpers.key_builder import (
        format_key,
    )

    spot_key = format_key("BTC", "SPOT")
    assert spot_key == "market:BTC_SPOT"

    option_key = format_key("BTC", "28FEB25", strike=30000.0, option_type="C")
    assert option_key == "market:BTC-28FEB25-30000-C"


@pytest.mark.parametrize(
    "iso,expected",
    [
        ("2025-02-28T16:00:00Z", "28FEB25"),
        ("2025-03-02T08:00:00+00:00", "2MAR25"),
    ],
)
def test_convert_iso_to_deribit(iso, expected):
    from common.redis_protocol.optimized_market_store_helpers.expiry_converter import (
        ExpiryConverter,
    )

    converter = ExpiryConverter()
    assert converter.convert_iso_to_deribit(iso) == expected


def test_convert_iso_to_deribit_invalid():
    from common.exceptions import DataError
    from common.redis_protocol.optimized_market_store_helpers.expiry_converter import (
        ExpiryConverter,
    )

    converter = ExpiryConverter()
    with pytest.raises(DataError):
        converter.convert_iso_to_deribit("invalid-date")


@pytest.mark.parametrize(
    "deribit,expected",
    [
        ("28FEB25", "2025-02-28T08:00:00+00:00"),
        ("2MAR25", "2025-03-02T08:00:00+00:00"),
    ],
)
def test_convert_expiry_to_iso(deribit, expected):
    from common.redis_protocol.optimized_market_store_helpers.expiry_converter import (
        ExpiryConverter,
    )

    converter = ExpiryConverter()
    assert converter.convert_expiry_to_iso(deribit) == expected


def test_convert_expiry_to_iso_invalid():
    from common.redis_protocol.optimized_market_store_helpers.expiry_converter import (
        ExpiryConverter,
    )

    converter = ExpiryConverter()
    assert converter.convert_expiry_to_iso("not-a-date") == "not-a-date"


def test_convert_expiry_to_iso_prior_epoch():
    from common.redis_protocol.optimized_market_store_helpers.expiry_converter import (
        ExpiryConverter,
    )

    converter = ExpiryConverter()
    assert converter.convert_expiry_to_iso("31DEC24") == "31DEC24"


def test_convert_expiry_to_iso_invalid_expiry_hour(monkeypatch):
    from common.redis_protocol.optimized_market_store_helpers.expiry_converter import (
        ExpiryConverter,
    )

    converter = ExpiryConverter()

    monkeypatch.setattr(
        "common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
        lambda *_args, **_kwargs: False,
        raising=False,
    )

    assert converter.convert_expiry_to_iso("28FEB25") == "28FEB25"


def test_convert_expiry_to_iso_raises_for_bad_month():
    from common.exceptions import DataError

    store = make_store({})
    with pytest.raises(DataError):
        store._convert_expiry_to_iso("28XYZ25")


@pytest.mark.asyncio
async def test_get_market_data_errors_when_missing_required_fields():
    from common.exceptions import DataError

    key = "market:BTC-SPOT"
    store = make_store({key: {"best_bid": "10"}})
    instrument = Instrument(
        instrument_name="BTC-TEST",
        currency="BTC",
        expiry=datetime(2025, 2, 28, 8, 0, tzinfo=timezone.utc),
        is_future=True,
    )

    with pytest.raises(DataError, match="missing best bid/ask"):
        await store.get_market_data(instrument, original_key=key)


@pytest.mark.asyncio
async def test_get_market_data_handles_conversion_errors(monkeypatch):
    from common.exceptions import ValidationError

    store = make_store({})
    instrument = Instrument(
        instrument_name="BTC-TEST",
        currency="BTC",
        expiry="invalid",
        is_future=True,
    )

    with pytest.raises(ValidationError, match="Invalid expiry"):
        await store.get_market_data(instrument)


@pytest.mark.asyncio
async def test_get_market_data_requires_expiry(monkeypatch):
    store = make_store({})
    instrument = SimpleNamespace(expiry=None)

    with pytest.raises(ValueError, match="missing expiry"):
        await store.get_market_data(instrument)


@pytest.mark.asyncio
async def test_get_market_data_returns_none_when_no_data():
    from common.exceptions import DataError

    store = make_store({})

    with pytest.raises(DataError, match="No Deribit market data"):
        await store.get_market_data(SimpleNamespace(), original_key="market:key")


@pytest.mark.asyncio
async def test_get_market_data_handles_type_errors():
    key = "market:key"
    store = make_store({key: {"best_bid": "1.1", "best_ask": "2.2", "odd": None}})

    result = await store.get_market_data(SimpleNamespace(), original_key=key)

    assert result["odd"] is None


@pytest.mark.asyncio
async def test_get_market_data_propagates_redis_errors():
    store = make_store({})
    store.initialized = False

    with pytest.raises(RuntimeError):
        await store.get_market_data(SimpleNamespace(), original_key="market:key")


@pytest.mark.asyncio
async def test_get_market_data_converts_numeric_fields():
    store = make_store({})
    instrument = Instrument(
        instrument_name="BTC-28FEB25-30000-C",
        currency="BTC",
        expiry=datetime(2025, 2, 28, 8, 0, tzinfo=timezone.utc),
        strike=30000.0,
        option_type="call",
        is_future=False,
    )

    descriptor = DeribitInstrumentDescriptor.from_instrument_data(
        kind="option",
        base_currency="BTC",
        quote_currency="USD",
        expiration_timestamp=int(instrument.expiry.timestamp()),
        strike=instrument.strike,
        option_type=instrument.option_type,
    )

    store.redis.mapping[descriptor.key] = {
        "best_bid": "101.5",
        "best_ask": "102.5",
        "best_bid_size": "3",
        "status": "open",
        "last_update": "stamp",
    }

    result = await store.get_market_data(instrument)

    assert result["best_bid"] == _VAL_101_5
    assert result["best_ask"] == _VAL_102_5
    assert result["best_bid_size"] == _TEST_COUNT_3
    assert result["status"] == "open"
    assert result["last_update"] == "stamp"


class ScanningRedis:
    def __init__(self, batches: List[List[str]], data_map: dict[str, dict[str, str]]):
        self._batches = list(batches)
        self._data_map = data_map

    async def scan(self, cursor: int = 0, match: str | None = None, count: int | None = None):
        if not self._batches:
            return 0, []
        batch = self._batches.pop(0)
        next_cursor = 0 if not self._batches else 1
        return next_cursor, list(batch)

    def pipeline(self):
        data_map = self._data_map

        class Pipeline:
            def __init__(self):
                self._keys: list[str] = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, _exc_type, _exc, _tb):
                return False

            def hgetall(self, key: str):
                self._keys.append(key)
                return self

            async def execute(self):
                return [data_map.get(key, {}) for key in self._keys]

        return Pipeline()


@pytest.mark.asyncio
async def test_get_all_instruments_builds_results(monkeypatch):
    future_key = DeribitInstrumentKey(instrument_type=DeribitInstrumentType.FUTURE, currency="BTC", expiry_iso="2025-02-28").key()
    option_key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.OPTION,
        currency="BTC",
        expiry_iso="2025-02-28",
        strike="30000",
        option_kind="c",
    ).key()
    other_key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.OPTION,
        currency="ETH",
        expiry_iso="2025-02-28",
        strike="2000",
        option_kind="p",
    ).key()

    data_map = {
        future_key: {"best_bid": "10", "best_ask": "11"},
        option_key: {
            "best_bid": "5",
            "best_ask": "6",
            "best_bid_size": "2",
            "best_ask_size": "3",
            "implied_volatility": "0.5",
        },
        other_key: {"best_bid": "1", "best_ask": "2"},
    }

    redis_stub = ScanningRedis([[future_key, option_key, other_key]], data_map)

    store = OptimizedMarketStore.__new__(OptimizedMarketStore)
    store.redis = redis_stub
    store.redis_pool = None
    store.initialized = True
    store.atomic_ops = None

    # Initialize required helpers
    from common.redis_protocol.optimized_market_store_helpers.instrument_fetcher import (
        InstrumentFetcher,
    )

    async def _get_redis():
        return store.redis

    store._instrument_fetcher = InstrumentFetcher(_get_redis)

    instruments = await store.get_all_instruments("BTC")

    assert len(instruments) == _TEST_COUNT_2
    futures = [instrument for instrument in instruments if instrument.is_future]
    options = [instrument for instrument in instruments if not instrument.is_future]
    assert futures and options
    assert futures[0].currency.lower() == "btc"
    assert options[0].option_type == "call"
    assert options[0].best_bid == _VAL_5_0


@pytest.mark.asyncio
async def test_get_all_instruments_returns_empty_when_no_keys(monkeypatch):
    store = OptimizedMarketStore.__new__(OptimizedMarketStore)
    store.initialized = True
    store.atomic_ops = None

    class NoKeysRedis:
        async def scan(self, *args, **kwargs):
            return 0, []

    redis_stub = NoKeysRedis()
    get_redis_mock = AsyncMock(return_value=redis_stub)
    monkeypatch.setattr(store, "_get_redis", get_redis_mock)

    # Initialize required helpers
    from common.redis_protocol.optimized_market_store_helpers.instrument_fetcher import (
        InstrumentFetcher,
    )

    store._instrument_fetcher = InstrumentFetcher(get_redis_mock)

    result = await store.get_all_instruments("BTC")

    assert result == []


@pytest.mark.asyncio
async def test_get_all_instruments_returns_empty_when_no_descriptors(monkeypatch):
    store = OptimizedMarketStore.__new__(OptimizedMarketStore)
    store.initialized = True
    store.atomic_ops = None

    class SingleKeyRedis:
        async def scan(self, *args, **kwargs):
            return 0, ["markets:deribit:future:eth:2025-02-28"]

    redis_stub = SingleKeyRedis()
    get_redis_mock = AsyncMock(return_value=redis_stub)
    monkeypatch.setattr(store, "_get_redis", get_redis_mock)

    # Initialize required helpers
    from common.redis_protocol.optimized_market_store_helpers.instrument_fetcher import (
        InstrumentFetcher,
    )

    store._instrument_fetcher = InstrumentFetcher(get_redis_mock)

    monkeypatch.setattr(
        "common.redis_protocol.optimized_market_store_helpers.instrument_fetcher_helpers.redis_scanner.parse_deribit_market_key",
        lambda key: SimpleNamespace(
            currency="ETH",
            expiry_iso="2025-02-28",
            strike=None,
            option_kind=None,
            instrument_type=DeribitInstrumentType.FUTURE,
        ),
    )

    result = await store.get_all_instruments("BTC")

    assert result == []


@pytest.mark.asyncio
async def test_get_all_instruments_handles_edge_cases(monkeypatch):
    store = OptimizedMarketStore.__new__(OptimizedMarketStore)
    store.initialized = True
    store.atomic_ops = None
    keys = _edge_case_keys()
    data_map = _edge_case_data_map()
    redis_stub = _RedisScanStub(keys, data_map)
    get_redis_mock = AsyncMock(return_value=redis_stub)
    monkeypatch.setattr(store, "_get_redis", get_redis_mock)

    # Initialize required helpers
    from common.redis_protocol.optimized_market_store_helpers.instrument_fetcher import (
        InstrumentFetcher,
    )

    store._instrument_fetcher = InstrumentFetcher(get_redis_mock)

    descriptor_map = _edge_case_descriptor_map()

    def fake_parse(key: str):
        if key == "bad-key":
            raise ValueError("bad key")
        return descriptor_map[key]

    monkeypatch.setattr(
        "common.redis_protocol.optimized_market_store_helpers.instrument_fetcher_helpers.redis_scanner.parse_deribit_market_key",
        fake_parse,
    )

    instruments = await store.get_all_instruments("BTC")

    assert any(instr.option_type == "call" for instr in instruments)
    assert any(instr.best_bid is None for instr in instruments)
