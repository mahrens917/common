"""Tests for trade_context module."""

from unittest.mock import MagicMock

import pytest

from common.kalshi_trading_client.client_helpers.trade_context import TradeContextResolver


class TestTradeContextResolver:
    """Tests for TradeContextResolver class."""

    def test_create_icao_to_city_mapping(self):
        mock_order_service = MagicMock()
        mock_order_service.create_icao_to_city_mapping.return_value = {"KJFK": "NYC", "KLAX": "LAX"}

        result = TradeContextResolver.create_icao_to_city_mapping(mock_order_service)

        assert result == {"KJFK": "NYC", "KLAX": "LAX"}
        mock_order_service.create_icao_to_city_mapping.assert_called_once()

    def test_extract_weather_station_from_ticker(self):
        mock_order_service = MagicMock()
        mock_order_service.extract_weather_station_from_ticker.return_value = "KJFK"

        result = TradeContextResolver.extract_weather_station_from_ticker(
            mock_order_service,
            "WEATHER-KJFK-HIGH",
        )

        assert result == "KJFK"
        mock_order_service.extract_weather_station_from_ticker.assert_called_once_with("WEATHER-KJFK-HIGH")

    def test_resolve_trade_context(self):
        mock_order_service = MagicMock()
        mock_order_service.resolve_trade_context.return_value = ("weather_high", "KJFK")

        result = TradeContextResolver.resolve_trade_context(
            mock_order_service,
            "WEATHER-KJFK-HIGH",
        )

        assert result == ("weather_high", "KJFK")
        mock_order_service.resolve_trade_context.assert_called_once_with("WEATHER-KJFK-HIGH")

    def test_get_weather_mapping(self):
        mock_resolver = MagicMock()
        mock_resolver.mapping = {"NYC": {"icao": "KJFK"}, "LAX": {"icao": "KLAX"}}

        result = TradeContextResolver.get_weather_mapping(mock_resolver)

        assert result == {"NYC": {"icao": "KJFK"}, "LAX": {"icao": "KLAX"}}

    def test_set_weather_mapping(self):
        mock_resolver = MagicMock()
        new_mapping = {"CHI": {"icao": "KORD"}}

        TradeContextResolver.set_weather_mapping(mock_resolver, new_mapping)

        mock_resolver.refresh.assert_called_once_with(new_mapping)
