"""Tests for common exception modules."""

from __future__ import annotations

import pytest

from src.common.exceptions import (
    APIError,
    ApplicationError,
    ConfigurationError,
    DataError,
    InvalidMarketDataError,
    MessageHandlerError,
    NetworkError,
    RedisError,
    ValidationError,
)
from src.common.exceptions.market import InvalidMarketDataError as MarketInvalidMarketDataError
from src.common.exceptions.market import (
    MarketError,
)
from src.common.exceptions.trading import (
    TradingError,
)
from src.common.exceptions.weather import (
    WeatherError,
    WeatherServiceError,
)


class TestMarketExceptions:
    """Tests for market exception classes."""

    def test_market_error_inherits_from_application_error(self) -> None:
        """MarketError inherits from ApplicationError."""
        assert issubclass(MarketError, ApplicationError)

    def test_market_error_can_be_raised(self) -> None:
        """MarketError can be raised and caught."""
        with pytest.raises(MarketError):
            raise MarketError()

    def test_invalid_market_data_error_inherits_from_both(self) -> None:
        """InvalidMarketDataError from market module inherits from MarketError and DataError."""
        assert issubclass(MarketInvalidMarketDataError, MarketError)
        assert issubclass(MarketInvalidMarketDataError, DataError)

    def test_invalid_market_data_error_can_be_raised(self) -> None:
        """InvalidMarketDataError can be raised and caught."""
        with pytest.raises(MarketInvalidMarketDataError):
            raise MarketInvalidMarketDataError()


class TestTradingExceptions:
    """Tests for trading exception classes."""

    def test_trading_error_inherits_from_application_error(self) -> None:
        """TradingError inherits from ApplicationError."""
        assert issubclass(TradingError, ApplicationError)

    def test_trading_error_can_be_raised(self) -> None:
        """TradingError can be raised and caught."""
        with pytest.raises(TradingError):
            raise TradingError()


class TestWeatherExceptions:
    """Tests for weather exception classes."""

    def test_weather_error_inherits_from_application_error(self) -> None:
        """WeatherError inherits from ApplicationError."""
        assert issubclass(WeatherError, ApplicationError)

    def test_weather_error_can_be_raised(self) -> None:
        """WeatherError can be raised and caught."""
        with pytest.raises(WeatherError):
            raise WeatherError()

    def test_weather_service_error_inherits_from_weather_error(self) -> None:
        """WeatherServiceError inherits from WeatherError."""
        assert issubclass(WeatherServiceError, WeatherError)

    def test_weather_service_error_can_be_raised(self) -> None:
        """WeatherServiceError can be raised and caught."""
        with pytest.raises(WeatherServiceError):
            raise WeatherServiceError()


class TestBaseExceptions:
    """Tests for base exception classes in __init__.py."""

    def test_application_error_with_default_message(self) -> None:
        """ApplicationError uses docstring as default message."""
        error = ApplicationError()
        assert str(error) != ""

    def test_application_error_with_custom_message(self) -> None:
        """ApplicationError uses custom message when provided."""
        error = ApplicationError("Custom error message")
        assert str(error) == "Custom error message"

    def test_application_error_stores_kwargs_as_attributes(self) -> None:
        """ApplicationError stores kwargs as attributes."""
        error = ApplicationError(field="test", value=123)
        assert error.field == "test"
        assert error.value == 123

    def test_configuration_error_default_message(self) -> None:
        """ConfigurationError has default message."""
        error = ConfigurationError()
        assert "Configuration" in str(error)

    def test_configuration_error_custom_message(self) -> None:
        """ConfigurationError uses custom message."""
        error = ConfigurationError("Missing config value")
        assert str(error) == "Missing config value"

    def test_validation_error_default_message(self) -> None:
        """ValidationError has default message."""
        error = ValidationError()
        assert "validation" in str(error).lower()

    def test_data_error_default_message(self) -> None:
        """DataError has default message."""
        error = DataError()
        assert "Data" in str(error)

    def test_network_error_default_message(self) -> None:
        """NetworkError has default message."""
        error = NetworkError()
        assert "Network" in str(error)

    def test_redis_error_default_message(self) -> None:
        """RedisError has default message."""
        error = RedisError()
        assert "Redis" in str(error)

    def test_api_error_default_message(self) -> None:
        """APIError has default message."""
        error = APIError()
        assert "API" in str(error)

    def test_invalid_market_data_error_default_message(self) -> None:
        """InvalidMarketDataError has default message."""
        error = InvalidMarketDataError()
        assert "Market" in str(error) or "market" in str(error)

    def test_message_handler_error_default_message(self) -> None:
        """MessageHandlerError has default message."""
        error = MessageHandlerError()
        assert "Message" in str(error) or "message" in str(error)
