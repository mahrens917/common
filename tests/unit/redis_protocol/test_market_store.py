from __future__ import annotations

import pytest

from common.exceptions import DataError, ValidationError
from common.redis_protocol.market_store import DeribitStore
from common.redis_schema import DeribitInstrumentKey, DeribitInstrumentType

_VAL_11_0 = 11.0


class AtomicStub:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    async def safe_market_data_read(self, key, required_fields=None):
        self.calls.append((key, tuple(required_fields or [])))
        return self.mapping.get(key, {})


class FakeRedis:
    def __init__(self, mapping):
        self.mapping = mapping

    async def hgetall(self, key):
        return self.mapping.get(key, {})


def make_store(mapping=None):
    store = DeribitStore.__new__(DeribitStore)
    store.redis = FakeRedis(mapping or {})
    store.redis_pool = None
    store._initialized = True
    store.atomic_ops = None
    return store


def test_deribit_store_requires_redis():
    with pytest.raises(TypeError):
        DeribitStore()


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_uses_atomic_ops():
    pair_key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="BTC",
        quote_currency="USDC",
    ).key()
    mapping = {pair_key: {"best_bid": "100.5", "best_ask": "101.5"}}
    store = make_store(mapping)
    store.atomic_ops = AtomicStub(mapping)

    bid, ask = await store.get_usdc_bid_ask_prices("BTC")

    assert bid == pytest.approx(100.5)
    assert ask == pytest.approx(101.5)
    assert store.atomic_ops.calls == [(pair_key, ("best_bid", "best_ask"))]


@pytest.mark.asyncio
async def test_get_usdc_bid_ask_prices_missing_fields():
    pair_key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="ETH",
        quote_currency="USDC",
    ).key()
    store = make_store({pair_key: {"best_bid": "2000"}})

    with pytest.raises(DataError):
        await store.get_usdc_bid_ask_prices("ETH")


@pytest.mark.asyncio
async def test_get_usdc_micro_price_uses_calculator(monkeypatch):
    pair_key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="SOL",
        quote_currency="USDC",
    ).key()
    payload = {
        "best_bid": "10",
        "best_ask": "12",
        "best_bid_size": "5",
        "best_ask_size": "7",
    }
    store = make_store({pair_key: payload})

    called_with = {}

    def fake_calculate(bid, ask, bid_size, ask_size):
        called_with["args"] = (bid, ask, bid_size, ask_size)
        return 11.0

    monkeypatch.setattr("common.utils.pricing.calculate_usdc_micro_price", fake_calculate)

    result = await store.get_usdc_micro_price("SOL")

    assert result == _VAL_11_0
    assert called_with["args"] == (10.0, 12.0, 5.0, 7.0)


@pytest.mark.asyncio
async def test_get_usdc_micro_price_missing_field():
    pair_key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="XRP",
        quote_currency="USDC",
    ).key()
    store = make_store({pair_key: {"best_bid": "1", "best_ask": "1.1"}})

    with pytest.raises(DataError):
        await store.get_usdc_micro_price("XRP")


@pytest.mark.asyncio
async def test_get_usdc_micro_price_invalid_values(monkeypatch):
    pair_key = DeribitInstrumentKey(
        instrument_type=DeribitInstrumentType.SPOT,
        currency="DOGE",
        quote_currency="USDC",
    ).key()
    store = make_store({pair_key: {"best_bid": "bad", "best_ask": "1", "best_bid_size": "1", "best_ask_size": "1"}})

    with pytest.raises(ValidationError):
        await store.get_usdc_micro_price("DOGE")
