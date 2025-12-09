"""Tests for Kalshi store interpolation helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.redis_protocol.kalshi_store import store_methods
from src.common.redis_schema import build_kalshi_market_key


class DummyStore:
    def __init__(self):
        self.logger = MagicMock()
        self._ensure = True
        self._scan_keys = [build_kalshi_market_key("KXHIGHUSD")]
        self._redis = MagicMock()
        self._redis.hgetall = AsyncMock(return_value={"t_yes_bid": "1", "t_yes_ask": "2"})
        self._string_or_default = lambda value, default=None: value or default
        self._int_or_default = lambda value, default=0: int(value) if value is not None else default
        self._float_or_default = lambda value, default=0.0: (
            float(value) if value is not None else default
        )

    async def _ensure_redis_connection(self):
        return self._ensure

    async def _scan_market_keys(self):
        return self._scan_keys

    async def _get_redis(self):
        return self._redis


@pytest.mark.asyncio
async def test_validate_market_for_interpolation_filters_currency():
    valid_key = build_kalshi_market_key("KXHIGHUSD")
    result = store_methods._validate_market_for_interpolation(
        valid_key, "USD", store_methods.logger
    )
    assert result is not None

    assert (
        store_methods._validate_market_for_interpolation("invalid:key", "USD", store_methods.logger)
        is None
    )
    # Currency mismatch
    different_key = build_kalshi_market_key("KXHIGHTESTEUR")
    assert (
        store_methods._validate_market_for_interpolation(different_key, "USD", store_methods.logger)
        is None
    )


def test_parse_bid_ask_prices_handles_invalid():
    logger = MagicMock()
    assert store_methods._parse_bid_ask_prices(None, None, "KXHIGHUSD", logger) is None

    assert store_methods._parse_bid_ask_prices("1", "2", "KXHIGHUSD", logger) == (1.0, 2.0)

    assert store_methods._parse_bid_ask_prices("abc", None, "KXHIGHUSD", logger) is None
    assert logger.warning.called


@pytest.mark.asyncio
async def test_process_market_for_interpolation_success(monkeypatch):
    store = DummyStore()
    redis = MagicMock()
    redis.hgetall = AsyncMock(
        return_value={
            "t_yes_bid": "1",
            "t_yes_ask": "2",
            "interpolation_method": None,
            "deribit_points_used": "3",
            "interpolation_quality_score": "4.5",
            "interpolation_timestamp": "ts",
            "interp_error_bid": "0.1",
            "interp_error_ask": "0.2",
        }
    )
    module_logger = MagicMock()

    result = await store_methods._process_market_for_interpolation(
        store, build_kalshi_market_key("KXHIGHUSD"), "USD", redis, module_logger
    )

    assert result is not None
    ticker, data = result
    assert ticker == "KXHIGHUSD"


@pytest.mark.asyncio
async def test_process_market_for_interpolation_skips_when_no_data():
    store = DummyStore()
    redis = MagicMock()
    redis.hgetall = AsyncMock(return_value={})

    result = await store_methods._process_market_for_interpolation(
        store, build_kalshi_market_key("KXHIGHUSD"), "USD", redis, MagicMock()
    )

    assert result is None


@pytest.mark.asyncio
async def test_process_market_for_interpolation_handles_extraction_error():
    store = DummyStore()
    redis = MagicMock()
    redis.hgetall = AsyncMock(
        return_value={"t_yes_bid": "1", "t_yes_ask": "2", "interpolation_method": "value"}
    )
    # make extraction fail
    store._string_or_default = lambda value, default=None: (_ for _ in ()).throw(ValueError("boom"))

    result = await store_methods._process_market_for_interpolation(
        store, build_kalshi_market_key("KXHIGHUSD"), "USD", redis, MagicMock()
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_interpolation_results_respects_connection(monkeypatch):
    store = DummyStore()
    store._ensure = False

    result = await store_methods.get_interpolation_results(store, "usd")
    assert result == {}


@pytest.mark.asyncio
async def test_get_interpolation_results_returns_entries(monkeypatch):
    store = DummyStore()
    store._redis.hgetall = AsyncMock(return_value={"t_yes_bid": "1", "t_yes_ask": "2"})
    monkeypatch.setattr(
        store_methods,
        "_process_market_for_interpolation",
        AsyncMock(return_value=("KXHIGHUSD", {"t_yes_bid": 1.0, "t_yes_ask": 2.0})),
    )

    result = await store_methods.get_interpolation_results(store, "usd")

    assert result["KXHIGHUSD"]["t_yes_bid"] == 1.0


@pytest.mark.asyncio
async def test_get_interpolation_results_handles_redis_error(monkeypatch):
    store = DummyStore()
    store._redis.hgetall = AsyncMock(side_effect=store_methods.REDIS_ERRORS[0])
    monkeypatch.setattr(
        store_methods, "_process_market_for_interpolation", AsyncMock(return_value=None)
    )
    store._scan_keys = [build_kalshi_market_key("KXHIGHUSD")]

    result = await store_methods.get_interpolation_results(store, "usd")
    assert result == {}
