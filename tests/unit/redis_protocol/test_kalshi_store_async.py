from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from src.common.exceptions import ValidationError
from src.common.redis_protocol.kalshi_store import KalshiStore
from src.common.redis_protocol.market_normalization import (
    convert_numeric_field,
    format_probability_value,
    sync_top_of_book_fields,
)

_VAL_13_0 = 13.0
_VAL_42_0 = 42.0

from src.common.redis_protocol.weather_station_resolver import WeatherStationResolver


def _make_store(monkeypatch, fake_redis_client_factory, schema_config_factory):
    config = schema_config_factory(kalshi_market_prefix="markets:kalshi")
    monkeypatch.setattr("src.common.redis_protocol.kalshi_store.SCHEMA", config, raising=False)
    fake = fake_redis_client_factory("src.common.redis_protocol.kalshi_store.get_redis_pool")
    resolver = WeatherStationResolver(lambda: {}, logger=logging.getLogger("tests.async"))
    store = KalshiStore(redis=fake, weather_resolver=resolver)
    store.redis = fake
    store._initialized = True
    store._ensure_redis_connection = AsyncMock(return_value=True)
    return store, fake


def test_convert_numeric_field_handles_mixed_inputs():
    assert convert_numeric_field("42") == _VAL_42_0
    assert convert_numeric_field("  ") is None
    assert convert_numeric_field(13) == _VAL_13_0
    assert convert_numeric_field(None) is None
    with pytest.raises(ValidationError):
        convert_numeric_field("bad")


def test_format_probability_value_trims_insignificant_zeroes():
    assert format_probability_value("0.1250000000") == "0.125"
    assert format_probability_value(1) == "1"


def test_format_probability_value_rejects_invalid_inputs():
    with pytest.raises(TypeError):
        format_probability_value("not-a-number")
    with pytest.raises(TypeError):
        format_probability_value(float("inf"))


def test_sync_top_of_book_fields_populates_scalars():
    snapshot = {
        "yes_bids": {"0.41": 5, "0.39": 10},
        "yes_asks": {"0.45": 7},
    }
    sync_top_of_book_fields(snapshot)
    assert snapshot["yes_bid"] == "0.41"
    assert snapshot["yes_bid_size"] == "5"
    assert snapshot["yes_ask"] == "0.45"
    assert snapshot["yes_ask_size"] == "7"


@pytest.mark.asyncio
async def test_write_enhanced_market_data_formats_values(
    monkeypatch, fake_redis_client_factory, schema_config_factory
):
    store, fake = _make_store(monkeypatch, fake_redis_client_factory, schema_config_factory)
    ticker = "KXBTC-TEST-MKT"

    persisted = await store.write_enhanced_market_data(
        ticker,
        {"prob_yes": 0.125, "prob_no": "0.8750000000"},
    )

    assert persisted is True
    key = store.get_market_key(ticker)
    assert fake.dump_hash(key) == {"prob_yes": "0.125", "prob_no": "0.875"}


@pytest.mark.asyncio
async def test_get_market_snapshot_normalises_hash(
    monkeypatch, fake_redis_client_factory, schema_config_factory
):
    store, fake = _make_store(monkeypatch, fake_redis_client_factory, schema_config_factory)
    ticker = "KXBTC-TEST-MKT"
    market_key = store.get_market_key(ticker)

    await fake.hset(
        market_key,
        mapping={
            "yes_bids": '{"0.34": 12}',
            "yes_asks": '{"0.37": 4}',
            "status": "open",
            "last_trade_price": "12",
        },
    )

    snapshot = await store.get_market_snapshot(ticker, include_orderbook=False)

    assert snapshot["yes_bid"] == "0.34"
    assert snapshot["yes_ask"] == "0.37"
    assert "yes_bids" not in snapshot
    assert "yes_asks" not in snapshot
