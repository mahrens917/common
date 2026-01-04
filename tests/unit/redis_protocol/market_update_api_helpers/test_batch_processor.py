"""Tests for batch_processor module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.market_update_api_helpers.batch_processor import (
    MarketSignal,
    add_signal_to_pipeline,
    build_market_signals,
    build_signal_mapping,
    fetch_kalshi_prices,
    filter_allowed_signals,
)


class TestBuildMarketSignals:
    """Tests for build_market_signals function."""

    def test_builds_signals_from_dict(self):
        signals = {
            "TICKER1": {"t_yes_bid": 50.0, "t_yes_ask": 55.0},
            "TICKER2": {"t_yes_bid": 60.0},
        }
        key_builder = lambda ticker: f"markets:test:{ticker}"

        result = build_market_signals(signals, "weather", key_builder)

        assert len(result) == 2
        assert result[0].ticker == "TICKER1"
        assert result[0].t_yes_bid == 50.0
        assert result[0].t_yes_ask == 55.0
        assert result[0].algo == "weather"
        assert result[1].ticker == "TICKER2"
        assert result[1].t_yes_bid == 60.0
        assert result[1].t_yes_ask is None


class TestFilterAllowedSignals:
    """Tests for filter_allowed_signals function."""

    @pytest.fixture
    def mock_redis(self):
        return MagicMock()

    @pytest.fixture
    def mock_ownership_func(self):
        async def check_ownership(redis, market_key, algo, ticker):
            return MagicMock(rejected=False)

        return check_ownership

    @pytest.mark.asyncio
    async def test_filters_signals_with_no_prices(self, mock_redis, mock_ownership_func):
        signals = [
            MarketSignal(
                ticker="TEST1",
                market_key="markets:test:TEST1",
                t_yes_bid=None,
                t_yes_ask=None,
                algo="weather",
            ),
            MarketSignal(
                ticker="TEST2",
                market_key="markets:test:TEST2",
                t_yes_bid=50.0,
                t_yes_ask=None,
                algo="weather",
            ),
        ]

        allowed, rejected, failed = await filter_allowed_signals(mock_redis, signals, "weather", mock_ownership_func)

        assert len(allowed) == 1
        assert allowed[0].ticker == "TEST2"
        assert failed == ["TEST1"]
        assert rejected == []

    @pytest.mark.asyncio
    async def test_filters_rejected_signals(self, mock_redis):
        async def reject_ownership(redis, market_key, algo, ticker):
            return MagicMock(rejected=True)

        signals = [
            MarketSignal(
                ticker="TEST1",
                market_key="markets:test:TEST1",
                t_yes_bid=50.0,
                t_yes_ask=None,
                algo="weather",
            ),
        ]

        allowed, rejected, failed = await filter_allowed_signals(mock_redis, signals, "weather", reject_ownership)

        assert allowed == []
        assert rejected == ["TEST1"]
        assert failed == []


class TestFetchKalshiPrices:
    """Tests for fetch_kalshi_prices function."""

    @pytest.mark.asyncio
    async def test_fetches_prices_for_signals(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.hmget = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[[b"10", b"20"], [b"15", b"25"]])
        mock_redis.pipeline.return_value = mock_pipe

        signals = [
            MarketSignal(
                ticker="TEST1",
                market_key="markets:test:TEST1",
                t_yes_bid=50.0,
                t_yes_ask=None,
                algo="weather",
            ),
            MarketSignal(
                ticker="TEST2",
                market_key="markets:test:TEST2",
                t_yes_bid=None,
                t_yes_ask=55.0,
                algo="weather",
            ),
        ]

        result = await fetch_kalshi_prices(mock_redis, signals)

        assert result == [[b"10", b"20"], [b"15", b"25"]]
        assert mock_pipe.hmget.call_count == 2


class TestBuildSignalMapping:
    """Tests for build_signal_mapping function."""

    def test_builds_mapping_with_bid(self):
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_yes_bid=50.0,
            t_yes_ask=None,
            algo="weather",
        )

        result = build_signal_mapping(sig, "SELL", "weather")

        assert result == {"algo": "weather", "direction": "SELL", "t_yes_bid": 50.0}

    def test_builds_mapping_with_ask(self):
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_yes_bid=None,
            t_yes_ask=55.0,
            algo="weather",
        )

        result = build_signal_mapping(sig, "BUY", "weather")

        assert result == {"algo": "weather", "direction": "BUY", "t_yes_ask": 55.0}

    def test_builds_mapping_with_both_prices(self):
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_yes_bid=50.0,
            t_yes_ask=55.0,
            algo="weather",
        )

        result = build_signal_mapping(sig, "NONE", "weather")

        assert result == {
            "algo": "weather",
            "direction": "NONE",
            "t_yes_bid": 50.0,
            "t_yes_ask": 55.0,
        }


class TestAddSignalToPipeline:
    """Tests for add_signal_to_pipeline function."""

    def test_adds_signal_with_bid_deletes_ask(self):
        mock_pipe = MagicMock()
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_yes_bid=50.0,
            t_yes_ask=None,
            algo="weather",
        )
        mapping = {"algo": "weather", "direction": "SELL", "t_yes_bid": 50.0}

        add_signal_to_pipeline(mock_pipe, sig, mapping)

        mock_pipe.hset.assert_called_once_with("markets:test:TEST", mapping=mapping)
        mock_pipe.hdel.assert_called_once_with("markets:test:TEST", "t_yes_ask")

    def test_adds_signal_with_ask_deletes_bid(self):
        mock_pipe = MagicMock()
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_yes_bid=None,
            t_yes_ask=55.0,
            algo="weather",
        )
        mapping = {"algo": "weather", "direction": "BUY", "t_yes_ask": 55.0}

        add_signal_to_pipeline(mock_pipe, sig, mapping)

        mock_pipe.hset.assert_called_once_with("markets:test:TEST", mapping=mapping)
        mock_pipe.hdel.assert_called_once_with("markets:test:TEST", "t_yes_bid")

    def test_adds_signal_with_both_prices_no_delete(self):
        mock_pipe = MagicMock()
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_yes_bid=50.0,
            t_yes_ask=55.0,
            algo="weather",
        )
        mapping = {"algo": "weather", "direction": "NONE", "t_yes_bid": 50.0, "t_yes_ask": 55.0}

        add_signal_to_pipeline(mock_pipe, sig, mapping)

        mock_pipe.hset.assert_called_once_with("markets:test:TEST", mapping=mapping)
        mock_pipe.hdel.assert_not_called()


class TestMarketSignal:
    """Tests for MarketSignal dataclass."""

    def test_create_market_signal(self):
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_yes_bid=50.0,
            t_yes_ask=55.0,
            algo="weather",
        )

        assert sig.ticker == "TEST"
        assert sig.market_key == "markets:test:TEST"
        assert sig.t_yes_bid == 50.0
        assert sig.t_yes_ask == 55.0
        assert sig.algo == "weather"
