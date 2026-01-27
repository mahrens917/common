"""Tests for batch_processor module."""

from unittest.mock import MagicMock

from common.redis_protocol.market_update_api_helpers.batch_processor import (
    MarketSignal,
    add_signal_to_pipeline,
    build_market_signals,
    build_signal_mapping,
    filter_valid_signals,
)


class TestBuildMarketSignals:
    """Tests for build_market_signals function."""

    def test_builds_signals_from_dict(self):
        signals = {
            "TICKER1": {"t_bid": 50.0, "t_ask": 55.0},
            "TICKER2": {"t_bid": 60.0},
        }
        key_builder = lambda ticker: f"markets:test:{ticker}"

        result = build_market_signals(signals, "weather", key_builder)

        assert len(result) == 2
        assert result[0].ticker == "TICKER1"
        assert result[0].t_bid == 50.0
        assert result[0].t_ask == 55.0
        assert result[0].algo == "weather"
        assert result[1].ticker == "TICKER2"
        assert result[1].t_bid == 60.0
        assert result[1].t_ask is None


class TestFilterValidSignals:
    """Tests for filter_valid_signals function."""

    def test_filters_signals_with_no_prices(self):
        signals = [
            MarketSignal(
                ticker="TEST1",
                market_key="markets:test:TEST1",
                t_bid=None,
                t_ask=None,
                algo="weather",
            ),
            MarketSignal(
                ticker="TEST2",
                market_key="markets:test:TEST2",
                t_bid=50.0,
                t_ask=None,
                algo="weather",
            ),
        ]

        valid, failed = filter_valid_signals(signals)

        assert len(valid) == 1
        assert valid[0].ticker == "TEST2"
        assert failed == ["TEST1"]

    def test_all_valid_signals(self):
        signals = [
            MarketSignal(
                ticker="TEST1",
                market_key="markets:test:TEST1",
                t_bid=50.0,
                t_ask=None,
                algo="weather",
            ),
            MarketSignal(
                ticker="TEST2",
                market_key="markets:test:TEST2",
                t_bid=None,
                t_ask=55.0,
                algo="weather",
            ),
        ]

        valid, failed = filter_valid_signals(signals)

        assert len(valid) == 2
        assert failed == []


class TestBuildSignalMapping:
    """Tests for build_signal_mapping function."""

    def test_builds_mapping_with_bid(self):
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_bid=50.0,
            t_ask=None,
            algo="weather",
        )

        result = build_signal_mapping(sig, "weather")

        # Only namespaced field, no algo/direction
        assert result == {"weather:t_bid": 50.0}

    def test_builds_mapping_with_ask(self):
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_bid=None,
            t_ask=55.0,
            algo="weather",
        )

        result = build_signal_mapping(sig, "weather")

        # Only namespaced field, no algo/direction
        assert result == {"weather:t_ask": 55.0}

    def test_builds_mapping_with_both_prices(self):
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_bid=50.0,
            t_ask=55.0,
            algo="weather",
        )

        result = build_signal_mapping(sig, "weather")

        # Only namespaced fields, no algo/direction
        assert result == {
            "weather:t_bid": 50.0,
            "weather:t_ask": 55.0,
        }


class TestAddSignalToPipeline:
    """Tests for add_signal_to_pipeline function."""

    def test_adds_signal_with_bid_deletes_ask(self):
        mock_pipe = MagicMock()
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_bid=50.0,
            t_ask=None,
            algo="weather",
        )
        mapping = {"weather:t_bid": 50.0}

        add_signal_to_pipeline(mock_pipe, sig, mapping)

        mock_pipe.hset.assert_called_once_with("markets:test:TEST", mapping=mapping)
        mock_pipe.hdel.assert_called_once_with("markets:test:TEST", "weather:t_ask")

    def test_adds_signal_with_ask_deletes_bid(self):
        mock_pipe = MagicMock()
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_bid=None,
            t_ask=55.0,
            algo="weather",
        )
        mapping = {"weather:t_ask": 55.0}

        add_signal_to_pipeline(mock_pipe, sig, mapping)

        mock_pipe.hset.assert_called_once_with("markets:test:TEST", mapping=mapping)
        mock_pipe.hdel.assert_called_once_with("markets:test:TEST", "weather:t_bid")

    def test_adds_signal_with_both_prices_no_delete(self):
        mock_pipe = MagicMock()
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_bid=50.0,
            t_ask=55.0,
            algo="weather",
        )
        mapping = {"weather:t_bid": 50.0, "weather:t_ask": 55.0}

        add_signal_to_pipeline(mock_pipe, sig, mapping)

        mock_pipe.hset.assert_called_once_with("markets:test:TEST", mapping=mapping)
        mock_pipe.hdel.assert_not_called()


class TestMarketSignal:
    """Tests for MarketSignal dataclass."""

    def test_create_market_signal(self):
        sig = MarketSignal(
            ticker="TEST",
            market_key="markets:test:TEST",
            t_bid=50.0,
            t_ask=55.0,
            algo="weather",
        )

        assert sig.ticker == "TEST"
        assert sig.market_key == "markets:test:TEST"
        assert sig.t_bid == 50.0
        assert sig.t_ask == 55.0
        assert sig.algo == "weather"
