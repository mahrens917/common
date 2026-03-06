"""Tests for common exception modules."""

from __future__ import annotations

import pytest

from common.exceptions import (
    APIError,
    ApplicationError,
    ConfigurationError,
    DataError,
    InvalidMarketDataError,
    MarketError,
    MessageHandlerError,
    NetworkError,
    RedisError,
    TradingError,
    ValidationError,
    WeatherError,
    WeatherServiceError,
)


class TestMarketExceptions:
    """Tests for market exception classes."""

    def test_market_error_inherits_from_application_error(self) -> None:
        assert issubclass(MarketError, ApplicationError)

    def test_market_error_can_be_raised(self) -> None:
        with pytest.raises(MarketError):
            raise MarketError()


class TestTradingExceptions:
    """Tests for trading exception classes."""

    def test_trading_error_inherits_from_application_error(self) -> None:
        assert issubclass(TradingError, ApplicationError)

    def test_trading_error_can_be_raised(self) -> None:
        with pytest.raises(TradingError):
            raise TradingError()


class TestWeatherExceptions:
    """Tests for weather exception classes."""

    def test_weather_error_inherits_from_application_error(self) -> None:
        assert issubclass(WeatherError, ApplicationError)

    def test_weather_error_can_be_raised(self) -> None:
        with pytest.raises(WeatherError):
            raise WeatherError()

    def test_weather_service_error_inherits_from_application_error(self) -> None:
        assert issubclass(WeatherServiceError, ApplicationError)

    def test_weather_service_error_can_be_raised(self) -> None:
        with pytest.raises(WeatherServiceError):
            raise WeatherServiceError()


class TestBaseExceptions:
    """Tests for base exception classes in __init__.py."""

    def test_application_error_with_default_message(self) -> None:
        error = ApplicationError()
        assert str(error) != ""

    def test_application_error_with_custom_message(self) -> None:
        error = ApplicationError("Custom error message")
        assert str(error) == "Custom error message"

    def test_application_error_stores_kwargs_as_attributes(self) -> None:
        error = ApplicationError(field="test", value=123)
        assert error.field == "test"
        assert error.value == 123

    def test_configuration_error_default_message(self) -> None:
        error = ConfigurationError()
        assert "Configuration" in str(error)

    def test_configuration_error_custom_message(self) -> None:
        error = ConfigurationError("Missing config value")
        assert str(error) == "Missing config value"

    def test_validation_error_default_message(self) -> None:
        error = ValidationError()
        assert "validation" in str(error).lower()

    def test_data_error_default_message(self) -> None:
        error = DataError()
        assert "Data" in str(error)

    def test_network_error_default_message(self) -> None:
        error = NetworkError()
        assert "Network" in str(error)

    def test_redis_error_default_message(self) -> None:
        error = RedisError()
        assert "Redis" in str(error)

    def test_api_error_default_message(self) -> None:
        error = APIError()
        assert "API" in str(error)

    def test_invalid_market_data_error_default_message(self) -> None:
        error = InvalidMarketDataError()
        assert "Market" in str(error) or "market" in str(error)

    def test_message_handler_error_default_message(self) -> None:
        error = MessageHandlerError()
        assert "Message" in str(error) or "message" in str(error)
