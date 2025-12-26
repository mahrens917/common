"""Tests for kalshi_catalog_helpers.market_filter_helpers.market_processor module."""

from unittest.mock import MagicMock

import pytest

from common.kalshi_catalog_helpers.market_filter_helpers.market_processor import (
    MarketProcessor,
)


class TestMarketProcessorInit:
    """Tests for MarketProcessor initialization."""

    def test_stores_dependencies(self) -> None:
        """Test initialization stores dependencies."""
        mock_crypto_detector = MagicMock()
        mock_weather_filter = MagicMock()
        mock_close_time_validator = MagicMock()

        processor = MarketProcessor(
            crypto_detector=mock_crypto_detector,
            weather_filter=mock_weather_filter,
            close_time_validator=mock_close_time_validator,
        )

        assert processor._crypto_detector == mock_crypto_detector
        assert processor._weather_filter == mock_weather_filter
        assert processor._close_time_validator == mock_close_time_validator


class TestMarketProcessorIsWeatherMarket:
    """Tests for _is_weather_market static method."""

    def test_weather_category(self) -> None:
        """Test Weather category returns True."""
        assert MarketProcessor._is_weather_market("Weather", "SOMEMARKET") is True

    def test_climate_category(self) -> None:
        """Test Climate and Weather category returns True."""
        assert MarketProcessor._is_weather_market("Climate and Weather", "SOMEMARKET") is True

    def test_kxhigh_ticker(self) -> None:
        """Test KXHIGH ticker prefix returns True."""
        assert MarketProcessor._is_weather_market("Other", "KXHIGHTEMP") is True

    def test_non_weather_market(self) -> None:
        """Test non-weather market returns False."""
        assert MarketProcessor._is_weather_market("Crypto", "KXBTC") is False


class TestMarketProcessorIsCryptoMarket:
    """Tests for _is_crypto_market method."""

    def test_crypto_category(self) -> None:
        """Test Crypto category returns True."""
        mock_crypto_detector = MagicMock()
        mock_crypto_detector.is_crypto_market.return_value = False
        processor = MarketProcessor(
            crypto_detector=mock_crypto_detector,
            weather_filter=MagicMock(),
            close_time_validator=MagicMock(),
        )

        market = {"ticker": "SOMETHING"}
        result = processor._is_crypto_market(market, "Crypto")

        assert result is True

    def test_detector_detected(self) -> None:
        """Test returns True when detector identifies crypto."""
        mock_crypto_detector = MagicMock()
        mock_crypto_detector.is_crypto_market.return_value = True
        processor = MarketProcessor(
            crypto_detector=mock_crypto_detector,
            weather_filter=MagicMock(),
            close_time_validator=MagicMock(),
        )

        market = {"ticker": "KXBTC-25JAN01"}
        result = processor._is_crypto_market(market, "Other")

        assert result is True

    def test_non_crypto(self) -> None:
        """Test returns False for non-crypto market."""
        mock_crypto_detector = MagicMock()
        mock_crypto_detector.is_crypto_market.return_value = False
        processor = MarketProcessor(
            crypto_detector=mock_crypto_detector,
            weather_filter=MagicMock(),
            close_time_validator=MagicMock(),
        )

        market = {"ticker": "KXMIA-25JAN01"}
        result = processor._is_crypto_market(market, "Weather")

        assert result is False


class TestMarketProcessorProcessMarket:
    """Tests for process_market method."""

    def test_processes_crypto_market(self) -> None:
        """Test processes crypto market."""
        mock_crypto_detector = MagicMock()
        mock_crypto_detector.is_crypto_market.return_value = True
        mock_weather_filter = MagicMock()
        mock_close_time_validator = MagicMock()
        mock_close_time_validator.is_in_future.return_value = True

        processor = MarketProcessor(
            crypto_detector=mock_crypto_detector,
            weather_filter=mock_weather_filter,
            close_time_validator=mock_close_time_validator,
        )

        market = {
            "__category": "Crypto",
            "ticker": "KXBTC-25JAN01-T100000",
            "strike_type": "greater",
            "floor_strike": "100000",
        }
        filtered: list[dict[str, object]] = []
        stats = {"crypto_total": 0, "crypto_kept": 0, "weather_total": 0, "weather_kept": 0, "other_total": 0}

        processor.process_market(market, filtered, stats, 1735000000.0)

        assert stats["crypto_total"] == 1

    def test_processes_weather_market(self) -> None:
        """Test processes weather market."""
        mock_crypto_detector = MagicMock()
        mock_crypto_detector.is_crypto_market.return_value = False
        mock_weather_filter = MagicMock()
        mock_weather_filter.passes_filters.return_value = True
        mock_close_time_validator = MagicMock()

        processor = MarketProcessor(
            crypto_detector=mock_crypto_detector,
            weather_filter=mock_weather_filter,
            close_time_validator=mock_close_time_validator,
        )

        market = {"__category": "Weather", "ticker": "KXMIA-25JAN01"}
        filtered: list[dict[str, object]] = []
        stats = {"crypto_total": 0, "crypto_kept": 0, "weather_total": 0, "weather_kept": 0, "other_total": 0}

        processor.process_market(market, filtered, stats, 1735000000.0)

        assert stats["weather_total"] == 1
        assert stats["weather_kept"] == 1
        assert len(filtered) == 1

    def test_processes_other_market(self) -> None:
        """Test processes other market."""
        mock_crypto_detector = MagicMock()
        mock_crypto_detector.is_crypto_market.return_value = False
        mock_weather_filter = MagicMock()
        mock_close_time_validator = MagicMock()

        processor = MarketProcessor(
            crypto_detector=mock_crypto_detector,
            weather_filter=mock_weather_filter,
            close_time_validator=mock_close_time_validator,
        )

        market = {"__category": "Politics", "ticker": "ELECTION-25JAN01"}
        filtered: list[dict[str, object]] = []
        stats = {"crypto_total": 0, "crypto_kept": 0, "weather_total": 0, "weather_kept": 0, "other_total": 0}

        processor.process_market(market, filtered, stats, 1735000000.0)

        assert stats["other_total"] == 1

    def test_handles_missing_ticker(self) -> None:
        """Test handles missing ticker."""
        mock_crypto_detector = MagicMock()
        mock_crypto_detector.is_crypto_market.return_value = False
        mock_weather_filter = MagicMock()
        mock_close_time_validator = MagicMock()

        processor = MarketProcessor(
            crypto_detector=mock_crypto_detector,
            weather_filter=mock_weather_filter,
            close_time_validator=mock_close_time_validator,
        )

        market = {"__category": "Politics"}  # No ticker
        filtered: list[dict[str, object]] = []
        stats = {"crypto_total": 0, "crypto_kept": 0, "weather_total": 0, "weather_kept": 0, "other_total": 0}

        processor.process_market(market, filtered, stats, 1735000000.0)

        assert stats["other_total"] == 1


class TestMarketProcessorPassesCryptoFilters:
    """Tests for _passes_crypto_filters method."""

    def test_fails_invalid_ticker(self) -> None:
        """Test fails with invalid ticker."""
        processor = MarketProcessor(
            crypto_detector=MagicMock(),
            weather_filter=MagicMock(),
            close_time_validator=MagicMock(),
        )

        market = {"ticker": "INVALID"}
        result = processor._passes_crypto_filters(market, 1735000000.0)

        assert result is False

    def test_fails_past_close_time(self) -> None:
        """Test fails when close time in past."""
        mock_close_time_validator = MagicMock()
        mock_close_time_validator.is_in_future.return_value = False
        processor = MarketProcessor(
            crypto_detector=MagicMock(),
            weather_filter=MagicMock(),
            close_time_validator=mock_close_time_validator,
        )

        market = {"ticker": "KXBTC-25JAN01-T100000"}
        result = processor._passes_crypto_filters(market, 1735000000.0)

        assert result is False

    def test_fails_invalid_strike_type(self) -> None:
        """Test fails with invalid strike type."""
        mock_close_time_validator = MagicMock()
        mock_close_time_validator.is_in_future.return_value = True
        processor = MarketProcessor(
            crypto_detector=MagicMock(),
            weather_filter=MagicMock(),
            close_time_validator=mock_close_time_validator,
        )

        market = {"ticker": "KXBTC-25JAN01-T100000", "strike_type": "invalid"}
        result = processor._passes_crypto_filters(market, 1735000000.0)

        assert result is False

    def test_handles_missing_ticker(self) -> None:
        """Test handles missing ticker."""
        processor = MarketProcessor(
            crypto_detector=MagicMock(),
            weather_filter=MagicMock(),
            close_time_validator=MagicMock(),
        )

        market: dict[str, object] = {}  # No ticker
        result = processor._passes_crypto_filters(market, 1735000000.0)

        assert result is False
