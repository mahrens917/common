"""Tests for Kalshi store helper utilities."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.store_methods import (
    _extract_interpolation_fields,
    _parse_bid_ask_prices,
    _process_market_for_interpolation,
    _validate_market_for_interpolation,
)


class DummyStore:
    def _string_or_default(self, value, default=""):
        return value or default

    def _int_or_default(self, value, default=0):
        return int(value) if value is not None else default

    def _float_or_default(self, value, default=0.0):
        return float(value) if value is not None else default


def test_validate_market_for_interpolation_handles_bad_key(monkeypatch):
    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.store_methods.parse_kalshi_market_key",
        lambda key: (_ for _ in ()).throw(ValueError("bad")),
    )

    assert _validate_market_for_interpolation("bad", "USD", MagicMock()) is None


def test_validate_market_for_interpolation_filters_currency(monkeypatch):
    class Descriptor:
        ticker = "ABC"

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.store_methods.parse_kalshi_market_key",
        lambda key: Descriptor(),
    )

    assert _validate_market_for_interpolation("key", "USD", MagicMock()) is None

    Descriptor.ticker = "USD-ABC"
    assert _validate_market_for_interpolation("key", "USD", MagicMock()) == ("key", "USD-ABC")


def test_parse_bid_ask_prices_warns_on_invalid(monkeypatch):
    logger = MagicMock()
    assert _parse_bid_ask_prices("a", "b", "ticker", logger) is None
    logger.warning.assert_called_once()

    assert _parse_bid_ask_prices(None, None, "ticker", logger) is None
    assert _parse_bid_ask_prices("1", "2", "ticker", logger) == (1.0, 2.0)


@pytest.mark.asyncio
async def test_process_market_for_interpolation_returns_when_data_present(monkeypatch):
    class Descriptor:
        ticker = "USD-ABC"

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.store_methods.parse_kalshi_market_key",
        lambda key: Descriptor(),
    )

    redis = MagicMock()
    redis.hgetall = AsyncMock(return_value={"t_yes_bid": "1", "t_yes_ask": "2"})

    def stub_extract(store, data):
        return {"extra": 1}

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.store_methods._extract_interpolation_fields",
        stub_extract,
    )

    store = DummyStore()
    result = await _process_market_for_interpolation(store, "key", "USD", redis, MagicMock())

    assert result[0] == "USD-ABC"
    assert result[1]["t_yes_bid"] == 1.0
    assert result[1]["t_yes_ask"] == 2.0
    assert result[1]["extra"] == 1


@pytest.mark.asyncio
async def test_process_market_for_interpolation_skips_when_no_market_data(monkeypatch):
    class Descriptor:
        ticker = "USD-ABC"

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.store_methods.parse_kalshi_market_key",
        lambda key: Descriptor(),
    )

    redis = MagicMock()
    redis.hgetall = AsyncMock(return_value={})

    store = DummyStore()
    assert await _process_market_for_interpolation(store, "key", "USD", redis, MagicMock()) is None
