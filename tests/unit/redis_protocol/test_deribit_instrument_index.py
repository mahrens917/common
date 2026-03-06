"""Tests for DeribitInstrumentIndex."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.deribit_instrument_index import DeribitInstrumentIndex


def _mock_market_store(scan_results: dict[str, dict]) -> MagicMock:
    """Build a mock market store that returns the given keys and data."""
    store = MagicMock()

    async def mock_get_redis_client():
        client = MagicMock()

        async def mock_scan(cursor=0, match="", count=10000):
            keys = [k for k in scan_results if match.replace("*", "") in k or True]
            return 0, keys

        client.scan = AsyncMock(side_effect=mock_scan)

        pipeline_instance = MagicMock()
        pipeline_instance.hgetall = MagicMock()

        async def mock_execute():
            return [scan_results.get(k, {}) for k in scan_results]

        pipeline_instance.execute = AsyncMock(side_effect=mock_execute)

        async def mock_pipeline():
            return pipeline_instance

        pipeline_ctx = MagicMock()
        pipeline_ctx.__aenter__ = AsyncMock(return_value=pipeline_instance)
        pipeline_ctx.__aexit__ = AsyncMock(return_value=False)
        client.pipeline = MagicMock(return_value=pipeline_ctx)

        return client

    store.get_redis_client = mock_get_redis_client
    return store


class TestDeribitInstrumentIndex:
    """Tests for DeribitInstrumentIndex initialization and lookups."""

    @pytest.mark.asyncio
    async def test_initialize_populates_instruments(self):
        scan_data = {
            "markets:deribit:option:BTC:2025-03-28:50000:c": {
                "instrument_type": "option",
                "currency": "BTC",
                "best_bid": "100.5",
                "best_ask": "102.0",
            },
            "markets:deribit:spot:BTC:USDC": {
                "instrument_type": "spot",
                "currency": "BTC",
                "best_bid": "65000",
                "best_ask": "65100",
            },
        }
        store = _mock_market_store(scan_data)
        index = DeribitInstrumentIndex()
        await index.initialize(store)

        assert index.instrument_count >= 1

    def test_apply_stream_update_new_instrument(self):
        index = DeribitInstrumentIndex()

        index.apply_stream_update(
            "markets:deribit:option:BTC:2025-03-28:50000:c",
            {"instrument_type": "option", "currency": "BTC", "best_bid": "100", "best_ask": "105"},
        )

        assert index.instrument_count == 1
        options = index.get_options_by_currency("BTC")
        assert len(options) == 1
        assert options[0]["best_bid"] == "100"

    def test_apply_stream_update_merges_existing(self):
        index = DeribitInstrumentIndex()

        index.apply_stream_update(
            "markets:deribit:option:BTC:2025-03-28:50000:c",
            {"instrument_type": "option", "currency": "BTC", "best_bid": "100", "best_ask": "105"},
        )
        index.apply_stream_update(
            "markets:deribit:option:BTC:2025-03-28:50000:c",
            {"best_bid": "110"},
        )

        options = index.get_options_by_currency("BTC")
        assert options[0]["best_bid"] == "110"
        assert options[0]["best_ask"] == "105"

    def test_get_futures_by_currency(self):
        index = DeribitInstrumentIndex()

        index.apply_stream_update(
            "markets:deribit:future:BTC:2025-03-28",
            {"instrument_type": "future", "currency": "BTC", "best_bid": "65000", "best_ask": "65100"},
        )

        futures = index.get_futures_by_currency("BTC")
        assert len(futures) == 1
        assert futures[0]["best_bid"] == "65000"

    def test_get_spot_price(self):
        index = DeribitInstrumentIndex()

        index.apply_stream_update(
            "markets:deribit:spot:BTC:USDC",
            {"instrument_type": "spot", "currency": "BTC", "best_bid": "65000", "best_ask": "65100"},
        )

        price = index.get_spot_price("BTC")
        assert price == 65050.0

    def test_get_spot_bid_ask(self):
        index = DeribitInstrumentIndex()

        index.apply_stream_update(
            "markets:deribit:spot:ETH:USDC",
            {"instrument_type": "spot", "currency": "ETH", "best_bid": "3500", "best_ask": "3510"},
        )

        result = index.get_spot_bid_ask("ETH")
        assert result is not None
        assert result == (3500.0, 3510.0)

    def test_get_spot_price_returns_none_when_missing(self):
        index = DeribitInstrumentIndex()

        assert index.get_spot_price("BTC") is None

    def test_get_spot_bid_ask_returns_none_when_missing(self):
        index = DeribitInstrumentIndex()

        assert index.get_spot_bid_ask("BTC") is None

    def test_currency_case_insensitive(self):
        index = DeribitInstrumentIndex()

        index.apply_stream_update(
            "markets:deribit:option:BTC:2025-03-28:50000:c",
            {"instrument_type": "option", "currency": "BTC", "best_bid": "100", "best_ask": "105"},
        )

        assert len(index.get_options_by_currency("btc")) == 1
        assert len(index.get_options_by_currency("BTC")) == 1

    def test_register_key_parses_from_key_when_fields_missing(self):
        index = DeribitInstrumentIndex()

        index.apply_stream_update(
            "markets:deribit:future:ETH:2025-06-27",
            {"best_bid": "4000", "best_ask": "4010"},
        )

        futures = index.get_futures_by_currency("ETH")
        assert len(futures) == 1


def _mock_deribit_redis(btc_count: int, eth_count: int) -> MagicMock:
    """Build a mock redis that returns per-currency key counts from SCAN."""
    redis = MagicMock()

    async def mock_scan(cursor=0, match="", count=10000):
        if "BTC" in match:
            keys = [f"markets:deribit:option:BTC:key-{i}" for i in range(btc_count)]
        elif "ETH" in match:
            keys = [f"markets:deribit:option:ETH:key-{i}" for i in range(eth_count)]
        else:
            keys = []
        return 0, keys

    redis.scan = AsyncMock(side_effect=mock_scan)
    return redis


class TestDeribitReconcile:
    """Tests for DeribitInstrumentIndex.reconcile."""

    @pytest.mark.asyncio
    async def test_matching_count_returns_false(self):
        index = DeribitInstrumentIndex()
        for i in range(8):
            index.apply_stream_update(
                f"markets:deribit:option:BTC:key-{i}",
                {"instrument_type": "option", "currency": "BTC", "best_bid": "100", "best_ask": "105"},
            )

        redis = _mock_deribit_redis(btc_count=8, eth_count=0)
        assert await index.reconcile(redis) is False

    @pytest.mark.asyncio
    async def test_within_tolerance_returns_false(self):
        index = DeribitInstrumentIndex()
        for i in range(10):
            index.apply_stream_update(
                f"markets:deribit:option:BTC:key-{i}",
                {"instrument_type": "option", "currency": "BTC", "best_bid": "100", "best_ask": "105"},
            )

        redis = _mock_deribit_redis(btc_count=14, eth_count=0)
        assert await index.reconcile(redis) is False

    @pytest.mark.asyncio
    async def test_diverged_count_returns_true(self, caplog):
        index = DeribitInstrumentIndex()
        for i in range(5):
            index.apply_stream_update(
                f"markets:deribit:option:BTC:key-{i}",
                {"instrument_type": "option", "currency": "BTC", "best_bid": "100", "best_ask": "105"},
            )

        redis = _mock_deribit_redis(btc_count=15, eth_count=5)
        with caplog.at_level(logging.WARNING):
            result = await index.reconcile(redis)

        assert result is True
        assert "count divergence" in caplog.text

    @pytest.mark.asyncio
    async def test_empty_cache_against_populated_redis(self, caplog):
        index = DeribitInstrumentIndex()

        redis = _mock_deribit_redis(btc_count=50, eth_count=30)
        with caplog.at_level(logging.WARNING):
            result = await index.reconcile(redis)

        assert result is True
