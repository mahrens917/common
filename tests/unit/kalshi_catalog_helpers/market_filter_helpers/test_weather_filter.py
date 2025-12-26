"""Tests for kalshi_catalog_helpers.market_filter_helpers.weather_filter module."""

from unittest.mock import MagicMock

import pytest

from common.kalshi_catalog_helpers.market_filter_helpers.weather_filter import (
    WeatherFilter,
)


class TestExtractStationToken:
    """Tests for extract_station_token static method."""

    def test_valid_ticker(self) -> None:
        """Test extracts station from valid ticker."""
        result = WeatherFilter.extract_station_token("KXHIGHPHX-25JAN15-T50")
        assert result == "PHX"

    def test_complex_station(self) -> None:
        """Test extracts multi-character station."""
        result = WeatherFilter.extract_station_token("KXHIGHDFW-25JAN15-T60")
        assert result == "DFW"

    def test_lowercase_input(self) -> None:
        """Test uppercases station."""
        result = WeatherFilter.extract_station_token("KXHIGHnyc-25JAN15-T50")
        assert result == "NYC"

    def test_no_suffix(self) -> None:
        """Test returns None for ticker without suffix."""
        result = WeatherFilter.extract_station_token("KXHIGH")
        assert result is None

    def test_empty_station(self) -> None:
        """Test returns None for empty station."""
        result = WeatherFilter.extract_station_token("KXHIGH-25JAN15")
        assert result is None


class TestPassesFilters:
    """Tests for passes_filters method."""

    def test_non_weather_ticker(self) -> None:
        """Test rejects non-weather ticker."""
        weather_filter = WeatherFilter(set())
        market = {"ticker": "KXBTC-25JAN15-T100000"}
        mock_validator = MagicMock()

        result = weather_filter.passes_filters(market, 1000.0, mock_validator)

        assert result is False

    def test_no_ticker(self) -> None:
        """Test rejects market without ticker."""
        weather_filter = WeatherFilter(set())
        market = {}
        mock_validator = MagicMock()

        result = weather_filter.passes_filters(market, 1000.0, mock_validator)

        assert result is False

    def test_none_ticker(self) -> None:
        """Test rejects market with None ticker."""
        weather_filter = WeatherFilter(set())
        market = {"ticker": None}
        mock_validator = MagicMock()

        result = weather_filter.passes_filters(market, 1000.0, mock_validator)

        assert result is False

    def test_expired_market(self) -> None:
        """Test rejects expired market."""
        weather_filter = WeatherFilter(set())
        market = {"ticker": "KXHIGHPHX-25JAN15-T50"}
        mock_validator = MagicMock()
        mock_validator.is_in_future.return_value = False

        result = weather_filter.passes_filters(market, 1000.0, mock_validator)

        assert result is False

    def test_valid_market_any_station(self) -> None:
        """Test accepts valid market with no station filter."""
        weather_filter = WeatherFilter(set())
        market = {"ticker": "KXHIGHPHX-25JAN15-T50"}
        mock_validator = MagicMock()
        mock_validator.is_in_future.return_value = True

        result = weather_filter.passes_filters(market, 1000.0, mock_validator)

        assert result is True

    def test_valid_market_matching_station(self) -> None:
        """Test accepts valid market matching station filter."""
        weather_filter = WeatherFilter({"PHX", "DFW"})
        market = {"ticker": "KXHIGHPHX-25JAN15-T50"}
        mock_validator = MagicMock()
        mock_validator.is_in_future.return_value = True

        result = weather_filter.passes_filters(market, 1000.0, mock_validator)

        assert result is True

    def test_valid_market_non_matching_station(self) -> None:
        """Test rejects valid market not matching station filter."""
        weather_filter = WeatherFilter({"PHX", "DFW"})
        market = {"ticker": "KXHIGHNYC-25JAN15-T50"}
        mock_validator = MagicMock()
        mock_validator.is_in_future.return_value = True

        result = weather_filter.passes_filters(market, 1000.0, mock_validator)

        assert result is False

    def test_invalid_station_token(self) -> None:
        """Test rejects ticker with invalid station token."""
        weather_filter = WeatherFilter(set())
        market = {"ticker": "KXHIGH-25JAN15-T50"}
        mock_validator = MagicMock()
        mock_validator.is_in_future.return_value = True

        result = weather_filter.passes_filters(market, 1000.0, mock_validator)

        assert result is False

    def test_lowercase_ticker(self) -> None:
        """Test handles lowercase ticker."""
        weather_filter = WeatherFilter(set())
        market = {"ticker": "kxhighphx-25jan15-t50"}
        mock_validator = MagicMock()
        mock_validator.is_in_future.return_value = True

        result = weather_filter.passes_filters(market, 1000.0, mock_validator)

        assert result is True
