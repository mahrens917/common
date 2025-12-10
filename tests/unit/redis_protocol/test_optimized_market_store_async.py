from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from common.redis_protocol.optimized_market_store import OptimizedMarketStore, logger
from common.redis_schema.markets import DeribitInstrumentKey, DeribitInstrumentType


def _make_store(fake):
    from types import MethodType

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
    store.redis = fake
    store.redis_pool = None
    store.initialized = True
    store.atomic_ops = None
    store.logger = logger

    # Bind the actual _get_redis method from OptimizedMarketStore
    store._get_redis = MethodType(OptimizedMarketStore._get_redis, store)

    # Initialize required helpers
    store.expiry_converter = ExpiryConverter()
    store.market_data_fetcher = MarketDataFetcher(store._get_redis)
    store.instrument_fetcher = InstrumentFetcher(store._get_redis)
    store.spot_price_fetcher = SpotPriceFetcher(store._get_redis, store.atomic_ops)
    return store


@pytest.mark.asyncio
async def test_get_spot_price_returns_mid(fake_redis):
    store = _make_store(fake_redis)
    key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="BTC",
        quote_currency="USDC",
    ).key()
    await fake_redis.hset(key, mapping={"best_bid": "30000", "best_ask": "30010"})

    spot = await store.get_spot_price("BTC")
    assert spot == pytest.approx(30005.0)


@pytest.mark.asyncio
async def test_get_spot_price_requires_market_data(fake_redis):
    from common.exceptions import DataError

    store = _make_store(fake_redis)
    with pytest.raises(DataError):
        await store.get_spot_price("XRP")


@pytest.mark.asyncio
async def test_get_spot_price_requires_expected_fields(fake_redis):
    store = _make_store(fake_redis)
    key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="BTC",
        quote_currency="USDC",
    ).key()
    await fake_redis.hset(key, mapping={"best_bid": "20000"})

    with pytest.raises(Exception):
        await store.get_spot_price("BTC")


@pytest.mark.asyncio
async def test_get_spot_price_validates_spread(fake_redis):
    from common.exceptions import ValidationError

    store = _make_store(fake_redis)
    key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="ETH",
        quote_currency="USDC",
    ).key()
    await fake_redis.hset(key, mapping={"best_bid": "1500", "best_ask": "1400"})

    with pytest.raises(ValidationError):
        await store.get_spot_price("ETH")


@pytest.mark.asyncio
async def test_get_spot_price_rejects_non_positive(fake_redis):
    from common.exceptions import ValidationError

    store = _make_store(fake_redis)
    key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="SOL",
        quote_currency="USDC",
    ).key()
    await fake_redis.hset(key, mapping={"best_bid": "-1", "best_ask": "0"})

    with pytest.raises(ValidationError):
        await store.get_spot_price("SOL")


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_validates(fake_redis):
    store = _make_store(fake_redis)
    key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="ETH",
        quote_currency="USDC",
    ).key()
    await fake_redis.hset(key, mapping={"best_bid": "2000.5", "best_ask": "2001.5"})

    bid, ask = await store.get_usdc_bid_ask_prices("ETH")
    assert bid == pytest.approx(2000.5)
    assert ask == pytest.approx(2001.5)


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_requires_fields(fake_redis):
    from common.exceptions import DataError

    store = _make_store(fake_redis)
    key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="SOL",
        quote_currency="USDC",
    ).key()
    await fake_redis.hset(key, mapping={"best_bid": "140"})

    with pytest.raises(DataError):
        await store.get_usdc_bid_ask_prices("SOL")


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_validates_numeric(fake_redis):
    from common.exceptions import ValidationError

    store = _make_store(fake_redis)
    key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="ADA",
        quote_currency="USDC",
    ).key()
    await fake_redis.hset(key, mapping={"best_bid": "not-a-number", "best_ask": "1"})

    with pytest.raises(ValidationError):
        await store.get_usdc_bid_ask_prices("ADA")


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_requires_market_data(fake_redis):
    from common.exceptions import DataError

    store = _make_store(fake_redis)

    with pytest.raises(DataError):
        await store.get_usdc_bid_ask_prices("XRP")


@pytest.mark.asyncio
async def test_create_logs_and_reraises(monkeypatch):
    monkeypatch.setattr(
        "common.redis_protocol.optimized_market_store_helpers.redis_initializer.get_redis_pool",
        AsyncMock(side_effect=RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError):
        await OptimizedMarketStore.create()


@pytest.mark.asyncio
async def test_get_options_by_currency_handles_errors(monkeypatch, fake_redis):
    store = _make_store(fake_redis)

    async def fail(_currency: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(store, "get_all_instruments", fail)

    result = await store.get_options_by_currency("BTC")

    assert result == []


@pytest.mark.asyncio
async def test_get_all_instruments_returns_empty_on_error(monkeypatch, fake_redis):
    store = _make_store(fake_redis)

    class FailingRedis:
        async def scan(self, *args, **kwargs):
            raise RuntimeError("scan failure")

    store.redis = FailingRedis()

    instruments = await store.get_all_instruments("BTC")

    assert instruments == []


@pytest.mark.asyncio
async def test_close_closes_redis():
    store = OptimizedMarketStore.__new__(OptimizedMarketStore)

    class DummyRedis:
        def __init__(self):
            self.closed = False

        async def aclose(self):
            self.closed = True

    dummy = DummyRedis()
    store.redis = dummy

    await store.close()

    assert dummy.closed


@pytest.mark.asyncio
async def test_get_options_by_currency_returns_empty_on_failure(monkeypatch):
    from common.redis_protocol.optimized_market_store_helpers.instrument_fetcher import (
        InstrumentFetcher,
    )

    store = OptimizedMarketStore.__new__(OptimizedMarketStore)
    store._instrument_fetcher = InstrumentFetcher(lambda: None)

    async def fail(_currency: str):
        raise RuntimeError("fail")

    monkeypatch.setattr(store._instrument_fetcher, "get_all_instruments", fail)

    result = await store.get_options_by_currency("BTC")

    assert result == []


@pytest.mark.asyncio
async def test_get_futures_by_currency_returns_empty_on_failure(monkeypatch):
    from common.redis_protocol.optimized_market_store_helpers.instrument_fetcher import (
        InstrumentFetcher,
    )

    store = OptimizedMarketStore.__new__(OptimizedMarketStore)
    store._instrument_fetcher = InstrumentFetcher(lambda: None)

    async def fail(_currency: str):
        raise RuntimeError("fail")

    monkeypatch.setattr(store._instrument_fetcher, "get_all_instruments", fail)

    result = await store.get_futures_by_currency("BTC")

    assert result == []


@pytest.mark.asyncio
async def test_get_puts_by_currency_returns_empty_on_failure(monkeypatch):
    from common.redis_protocol.optimized_market_store_helpers.instrument_fetcher import (
        InstrumentFetcher,
    )

    store = OptimizedMarketStore.__new__(OptimizedMarketStore)
    store._instrument_fetcher = InstrumentFetcher(lambda: None)

    async def fail(_currency: str):
        raise RuntimeError("fail")

    monkeypatch.setattr(store._instrument_fetcher, "get_all_instruments", fail)

    result = await store.get_puts_by_currency("BTC")

    assert result == []
