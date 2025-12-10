"""Tests for trading_exceptions_operational module."""

from __future__ import annotations

import pytest

from common.trading_exceptions_operational import (
    KalshiAPIError,
    KalshiConfigurationError,
    KalshiDataIntegrityError,
    KalshiNetworkError,
    KalshiOrderNotFoundError,
    KalshiOrderPollingError,
    KalshiPositionError,
    KalshiTradeNotificationError,
    KalshiTradePersistenceError,
)


class TestKalshiNetworkError:
    """Tests for KalshiNetworkError exception."""

    def test_init_with_message_only(self) -> None:
        """Initializes with message only."""
        error = KalshiNetworkError("Connection timed out")

        assert str(error) == "Connection timed out"
        assert error.error_code == "NETWORK_ERROR"
        assert error.operation_name is None
        assert error.underlying_error is None

    def test_init_with_all_params(self) -> None:
        """Initializes with all parameters."""
        underlying = ValueError("Socket error")
        error = KalshiNetworkError(
            message="Connection failed",
            operation_name="fetch_markets",
            underlying_error=underlying,
        )

        assert str(error) == "Connection failed"
        assert error.error_code == "NETWORK_ERROR"
        assert error.operation_name == "fetch_markets"
        assert error.underlying_error is underlying
        assert "Socket error" in error.request_data["underlying_error"]

    def test_stores_underlying_error_string(self) -> None:
        """Stores underlying error as string in request_data."""
        underlying = RuntimeError("DNS resolution failed")
        error = KalshiNetworkError("Network error", underlying_error=underlying)

        assert error.request_data["underlying_error"] == "DNS resolution failed"

    def test_handles_none_underlying_error(self) -> None:
        """Handles None underlying error."""
        error = KalshiNetworkError("Network error", underlying_error=None)

        assert error.request_data["underlying_error"] is None


class TestKalshiAPIError:
    """Tests for KalshiAPIError exception."""

    def test_init_with_message_only(self) -> None:
        """Initializes with message only."""
        error = KalshiAPIError("API request failed")

        assert str(error) == "API request failed"
        assert error.error_code == "API_ERROR"
        assert error.status_code is None
        assert error.response_data is None

    def test_init_with_all_params(self) -> None:
        """Initializes with all parameters."""
        response = {"error": "Invalid request", "code": "INVALID_REQUEST"}
        error = KalshiAPIError(
            message="API error occurred",
            status_code=400,
            response_data=response,
            operation_name="place_order",
        )

        assert str(error) == "API error occurred"
        assert error.error_code == "API_ERROR"
        assert error.status_code == 400
        assert error.response_data == response
        assert error.operation_name == "place_order"

    def test_stores_status_code_in_request_data(self) -> None:
        """Stores status code in request_data."""
        error = KalshiAPIError("Error", status_code=503)

        assert error.request_data["status_code"] == 503

    def test_stores_response_data_in_request_data(self) -> None:
        """Stores response data in request_data."""
        response = {"message": "Rate limited"}
        error = KalshiAPIError("Rate limit", response_data=response)

        assert error.request_data["response_data"] == response


class TestKalshiDataIntegrityError:
    """Tests for KalshiDataIntegrityError exception."""

    def test_init_with_message_only(self) -> None:
        """Initializes with message only."""
        error = KalshiDataIntegrityError("Data validation failed")

        assert str(error) == "Data validation failed"
        assert error.error_code == "DATA_INTEGRITY_ERROR"
        assert error.validation_errors == []

    def test_init_with_all_params(self) -> None:
        """Initializes with all parameters."""
        validation_errors = ["Field 'price' is required", "Field 'quantity' must be positive"]
        data = {"price": None, "quantity": -1}
        error = KalshiDataIntegrityError(
            message="Validation failed",
            validation_errors=validation_errors,
            operation_name="validate_order",
            data=data,
        )

        assert error.validation_errors == validation_errors
        assert error.operation_name == "validate_order"
        assert error.request_data["validation_errors"] == validation_errors
        assert error.request_data["invalid_data"] == data

    def test_validation_errors_defaults_to_empty_list(self) -> None:
        """validation_errors defaults to empty list when None."""
        error = KalshiDataIntegrityError("Error", validation_errors=None)

        assert error.validation_errors == []


class TestKalshiOrderNotFoundError:
    """Tests for KalshiOrderNotFoundError exception."""

    def test_init_with_message_only(self) -> None:
        """Initializes with message only."""
        error = KalshiOrderNotFoundError("Order not found")

        assert str(error) == "Order not found"
        assert error.error_code == "ORDER_NOT_FOUND"
        assert error.order_id is None
        assert error.client_order_id is None

    def test_init_with_all_params(self) -> None:
        """Initializes with all parameters."""
        error = KalshiOrderNotFoundError(
            message="Order does not exist",
            order_id="ord_12345",
            client_order_id="client_99",
            operation_name="get_order",
        )

        assert error.order_id == "ord_12345"
        assert error.client_order_id == "client_99"
        assert error.operation_name == "get_order"
        assert error.request_data["order_id"] == "ord_12345"
        assert error.request_data["client_order_id"] == "client_99"


class TestKalshiPositionError:
    """Tests for KalshiPositionError exception."""

    def test_init_with_message_only(self) -> None:
        """Initializes with message only."""
        error = KalshiPositionError("Position error")

        assert str(error) == "Position error"
        assert error.error_code == "POSITION_ERROR"
        assert error.ticker is None

    def test_init_with_all_params(self) -> None:
        """Initializes with all parameters."""
        position_data = {"contracts": 100, "avg_price": 0.55}
        error = KalshiPositionError(
            message="Position limit exceeded",
            ticker="BTCUSD-25JAN",
            operation_name="check_position",
            position_data=position_data,
        )

        assert error.ticker == "BTCUSD-25JAN"
        assert error.operation_name == "check_position"
        assert error.request_data["ticker"] == "BTCUSD-25JAN"
        assert error.request_data["position_data"] == position_data


class TestKalshiConfigurationError:
    """Tests for KalshiConfigurationError exception."""

    def test_init_with_message_only(self) -> None:
        """Initializes with message only."""
        error = KalshiConfigurationError("Config missing")

        assert str(error) == "Config missing"
        assert error.error_code == "CONFIGURATION_ERROR"
        assert error.config_key is None

    def test_init_with_all_params(self) -> None:
        """Initializes with all parameters."""
        error = KalshiConfigurationError(
            message="API key not found",
            config_key="KALSHI_API_KEY",
            operation_name="initialize_client",
        )

        assert error.config_key == "KALSHI_API_KEY"
        assert error.operation_name == "initialize_client"
        assert error.request_data["config_key"] == "KALSHI_API_KEY"


class TestKalshiOrderPollingError:
    """Tests for KalshiOrderPollingError exception."""

    def test_init_with_message_only(self) -> None:
        """Initializes with message only."""
        error = KalshiOrderPollingError("Polling failed")

        assert str(error) == "Polling failed"
        assert error.error_code == "ORDER_POLLING_FAILED"
        assert error.order_id is None

    def test_init_with_all_params(self) -> None:
        """Initializes with all parameters."""
        request_data = {"timeout": 30, "retries": 3}
        error = KalshiOrderPollingError(
            message="Order polling timed out",
            order_id="ord_abc123",
            operation_name="poll_order_fills",
            request_data=request_data,
        )

        assert error.order_id == "ord_abc123"
        assert error.operation_name == "poll_order_fills"
        assert error.request_data["order_id"] == "ord_abc123"
        assert error.request_data["timeout"] == 30
        assert error.request_data["retries"] == 3

    def test_merges_request_data(self) -> None:
        """Merges additional request_data with order_id."""
        error = KalshiOrderPollingError(
            message="Error",
            order_id="ord_1",
            request_data={"extra": "value"},
        )

        assert error.request_data["order_id"] == "ord_1"
        assert error.request_data["extra"] == "value"

    def test_handles_none_request_data(self) -> None:
        """Handles None request_data."""
        error = KalshiOrderPollingError(
            message="Error",
            order_id="ord_1",
            request_data=None,
        )

        assert error.request_data["order_id"] == "ord_1"


class TestKalshiTradePersistenceError:
    """Tests for KalshiTradePersistenceError exception."""

    def test_init_with_message_only(self) -> None:
        """Initializes with message only."""
        error = KalshiTradePersistenceError("Persistence failed")

        assert str(error) == "Persistence failed"
        assert error.error_code == "TRADE_PERSISTENCE_FAILED"
        assert error.order_id is None
        assert error.ticker is None

    def test_init_with_all_params(self) -> None:
        """Initializes with all parameters."""
        error = KalshiTradePersistenceError(
            message="Failed to persist trade",
            order_id="ord_xyz",
            ticker="WEATHER-HIGH-25JAN",
            operation_name="save_trade",
        )

        assert error.order_id == "ord_xyz"
        assert error.ticker == "WEATHER-HIGH-25JAN"
        assert error.operation_name == "save_trade"
        assert error.request_data["order_id"] == "ord_xyz"
        assert error.request_data["ticker"] == "WEATHER-HIGH-25JAN"


class TestKalshiTradeNotificationError:
    """Tests for KalshiTradeNotificationError exception."""

    def test_init_with_message_only(self) -> None:
        """Initializes with message only."""
        error = KalshiTradeNotificationError("Notification failed")

        assert str(error) == "Notification failed"
        assert error.error_code == "TRADE_NOTIFICATION_FAILED"
        assert error.order_id is None

    def test_init_with_all_params(self) -> None:
        """Initializes with all parameters."""
        error = KalshiTradeNotificationError(
            message="Telegram notification failed",
            order_id="ord_notify_1",
            operation_name="send_telegram",
        )

        assert error.order_id == "ord_notify_1"
        assert error.operation_name == "send_telegram"
        assert error.request_data["order_id"] == "ord_notify_1"


class TestExceptionInheritance:
    """Tests for exception inheritance."""

    def test_all_inherit_from_kalshi_trading_error(self) -> None:
        """All exceptions inherit from KalshiTradingError."""
        from common.trading_exceptions_core import KalshiTradingError

        exceptions = [
            KalshiNetworkError("msg"),
            KalshiAPIError("msg"),
            KalshiDataIntegrityError("msg"),
            KalshiOrderNotFoundError("msg"),
            KalshiPositionError("msg"),
            KalshiConfigurationError("msg"),
            KalshiOrderPollingError("msg"),
            KalshiTradePersistenceError("msg"),
            KalshiTradeNotificationError("msg"),
        ]

        for exc in exceptions:
            assert isinstance(exc, KalshiTradingError)

    def test_all_are_exception_subclasses(self) -> None:
        """All exceptions are Exception subclasses."""
        exceptions = [
            KalshiNetworkError("msg"),
            KalshiAPIError("msg"),
            KalshiDataIntegrityError("msg"),
            KalshiOrderNotFoundError("msg"),
            KalshiPositionError("msg"),
            KalshiConfigurationError("msg"),
            KalshiOrderPollingError("msg"),
            KalshiTradePersistenceError("msg"),
            KalshiTradeNotificationError("msg"),
        ]

        for exc in exceptions:
            assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        """All exceptions can be raised and caught."""
        with pytest.raises(KalshiNetworkError):
            raise KalshiNetworkError("Test network error")

        with pytest.raises(KalshiAPIError):
            raise KalshiAPIError("Test API error")

        with pytest.raises(KalshiDataIntegrityError):
            raise KalshiDataIntegrityError("Test data error")

        with pytest.raises(KalshiOrderNotFoundError):
            raise KalshiOrderNotFoundError("Test order not found")

        with pytest.raises(KalshiPositionError):
            raise KalshiPositionError("Test position error")

        with pytest.raises(KalshiConfigurationError):
            raise KalshiConfigurationError("Test config error")

        with pytest.raises(KalshiOrderPollingError):
            raise KalshiOrderPollingError("Test polling error")

        with pytest.raises(KalshiTradePersistenceError):
            raise KalshiTradePersistenceError("Test persistence error")

        with pytest.raises(KalshiTradeNotificationError):
            raise KalshiTradeNotificationError("Test notification error")
