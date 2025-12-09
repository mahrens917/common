import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from src.common.redis_protocol.optimized_market_store import OptimizedMarketStore
from src.common.redis_protocol.optimized_market_store_helpers.instrument_fetcher import (
    InstrumentFetcher,
)
from src.common.redis_protocol.optimized_market_store_helpers.instrument_fetcher_helpers.redis_scanner import (
    RedisInstrumentScanner,
)


class _DummyPipeline:
    def __init__(self, data_map: dict[str, dict[str, Any]]):
        self._keys: list[str] = []
        self._data_map = data_map

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def hgetall(self, key: str) -> None:
        self._keys.append(key)

    async def execute(self):
        return [self._data_map.get(key, {}) for key in self._keys]


class _DummyRedis:
    def __init__(self, scan_results: list[tuple[int, set[str]]], data_map: dict[str, dict]):
        self._scan_results = scan_results
        self._data_map = data_map
        self._scan_calls: list[str] = []

    async def scan(self, *, cursor: int, match: str, count: int):
        self._scan_calls.append(match)
        return self._scan_results.pop(0)

    def pipeline(self):
        return _DummyPipeline(self._data_map)

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_redis_instrument_scanner_fetches_data(monkeypatch):
    dummy_descriptor = SimpleNamespace(
        currency="btc", expiry_iso="2025-01-01", strike=100, option_kind="c", instrument_type="opt"
    )

    async def fake_get_redis():
        return _DummyRedis(
            [(0, {"markets:deribit:abc:btc"})], {"markets:deribit:abc:btc": {"k": b"1"}}
        )

    monkeypatch.setattr(
        "src.common.redis_protocol.optimized_market_store_helpers.instrument_fetcher_helpers.redis_scanner.parse_deribit_market_key",
        lambda key: dummy_descriptor,
    )

    scanner = RedisInstrumentScanner(fake_get_redis)
    results = await scanner.scan_and_fetch_instruments("BTC")

    assert results == [
        ("markets:deribit:abc:btc", dummy_descriptor, {"k": b"1"}),
    ]


@pytest.mark.asyncio
async def test_redis_instrument_scanner_handles_errors(monkeypatch):
    async def broken_get_redis():
        raise RuntimeError("boom")

    scanner = RedisInstrumentScanner(broken_get_redis)
    assert await scanner.scan_and_fetch_instruments("ETH") == []


class _FakeFetcher:
    def __init__(self, values):
        self.values = values

    async def get_all_instruments(self, currency):
        return self.values


@pytest.mark.asyncio
async def test_instrument_fetcher_filters_and_handles_errors(monkeypatch):
    fetcher = InstrumentFetcher(lambda: None)

    async def fake_scan(currency):
        return [("k", SimpleNamespace(expiry_iso="2024-01-01"), {"best_bid": "1.0"})]

    def fake_build(results):
        return [
            SimpleNamespace(is_future=False, option_type="put"),
            SimpleNamespace(is_future=True, option_type="call"),
        ]

    fetcher._scanner.scan_and_fetch_instruments = fake_scan  # type: ignore[attr-defined]
    fetcher._builder.build_instruments = fake_build  # type: ignore[attr-defined]

    all_instruments = await fetcher.get_all_instruments("BTC")
    assert len(all_instruments) == 2
    assert len(await fetcher.get_options_by_currency("BTC")) == 1
    assert len(await fetcher.get_futures_by_currency("BTC")) == 1
    assert len(await fetcher.get_puts_by_currency("BTC")) == 1

    async def failing_scan(currency):
        raise RuntimeError("redis down")

    fetcher._scanner.scan_and_fetch_instruments = failing_scan  # type: ignore[attr-defined]
    assert await fetcher.get_all_instruments("BTC") == []


class _StubFetcher:
    def __init__(self, values):
        self.values = values

    async def get_spot_price(self, currency):
        return 123.45

    async def get_usdc_bid_ask_prices(self, currency):
        return (1.0, 2.0)

    async def get_market_data(self, instrument, original_key=None):
        return {"k": "v"}

    async def get_all_instruments(self, currency):
        if isinstance(self.values, Exception):
            raise self.values
        return self.values


class _StubInitializer:
    @staticmethod
    def initialize_from_pool_or_client(redis_or_pool):
        class _Redis:
            async def aclose(self):
                return None

        return (_Redis(), None, True, "atomic")


class _FailingInitializer:
    @staticmethod
    def initialize_from_pool_or_client(redis_or_pool):
        return (None, None, False, None)


@pytest.mark.asyncio
async def test_optimized_market_store_happy_path(monkeypatch):
    monkeypatch.setattr(
        "src.common.redis_protocol.optimized_market_store.RedisInitializer", _StubInitializer
    )

    store = OptimizedMarketStore("redis")
    stub = _StubFetcher([SimpleNamespace(is_future=False, option_type="put")])
    store.spot_price_fetcher = stub  # type: ignore[assignment]
    store.market_data_fetcher = stub  # type: ignore[assignment]
    store.instrument_fetcher = stub  # type: ignore[assignment]
    store.atomic_ops = "ops"

    assert await store.get_spot_price("BTC") == 123.45
    assert await store.get_usdc_bid_ask_prices("BTC") == (1.0, 2.0)
    assert await store.get_market_data(SimpleNamespace()) == {"k": "v"}
    assert await store.get_options_by_currency("BTC") == stub.values
    assert await store.get_puts_by_currency("BTC") == stub.values
    assert await store.get_futures_by_currency("BTC") == []
    assert store._convert_expiry_to_iso("01JAN25") is not None
    assert store._convert_iso_to_deribit("2025-01-01") is not None
    await store.close()


@pytest.mark.asyncio
async def test_optimized_market_store_handles_errors(monkeypatch):
    monkeypatch.setattr(
        "src.common.redis_protocol.optimized_market_store.RedisInitializer", _StubInitializer
    )
    store = OptimizedMarketStore("redis")
    store.instrument_fetcher = _StubFetcher(Exception("fail"))  # type: ignore[assignment]
    assert await store.get_all_instruments("BTC") == []
    assert await store.get_options_by_currency("BTC") == []
    assert await store.get_puts_by_currency("BTC") == []
    assert await store.get_futures_by_currency("BTC") == []

    monkeypatch.setattr(
        "src.common.redis_protocol.optimized_market_store.RedisInitializer", _FailingInitializer
    )
    store2 = OptimizedMarketStore("redis")
    with pytest.raises(RuntimeError):
        await store2._get_redis()
