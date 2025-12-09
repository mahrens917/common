from datetime import datetime, timezone

import pytest

from src.common.trading_exceptions import (
    KalshiAPIError,
    KalshiAuthenticationError,
    KalshiConfigurationError,
    KalshiDataIntegrityError,
    KalshiInsufficientFundsError,
    KalshiMarketClosedError,
    KalshiNetworkError,
    KalshiOrderNotFoundError,
    KalshiOrderPollingError,
    KalshiOrderRejectedError,
    KalshiOrderValidationError,
    KalshiPositionError,
    KalshiRateLimiterBugError,
    KalshiRateLimiterQueueFullError,
    KalshiRateLimitError,
    KalshiTradeNotificationError,
    KalshiTradePersistenceError,
    KalshiTradingError,
)

_CONST_100 = 100
_HTTP_400 = 400
_HTTP_500 = 500
_TEST_COUNT_7 = 7


def test_trading_error_to_dict_includes_context(monkeypatch):
    fixed_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("src.common.time_utils.get_current_utc", lambda: fixed_now)

    err = KalshiTradingError(
        message="failure",
        error_code="FAILURE",
        operation_name="create_order",
        request_data={"order": 1},
    )

    payload = err.to_dict()

    assert payload["error_type"] == "KalshiTradingError"
    assert payload["message"] == "failure"
    assert payload["error_code"] == "FAILURE"
    assert payload["operation_name"] == "create_order"
    assert payload["request_data"] == {"order": 1}
    assert payload["timestamp"] == fixed_now.isoformat()


def test_insufficient_funds_error_sets_request_data(monkeypatch):
    monkeypatch.setattr(
        "src.common.time_utils.get_current_utc",
        lambda: datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
    )

    err = KalshiInsufficientFundsError(
        message="balance too low",
        required_balance_cents=500,
        available_balance_cents=100,
        operation_name="create_order",
    )

    assert err.error_code == "INSUFFICIENT_FUNDS"
    assert err.required_balance_cents == _HTTP_500
    assert err.available_balance_cents == _CONST_100
    assert err.request_data == {
        "required_balance_cents": 500,
        "available_balance_cents": 100,
    }
    assert err.to_dict()["request_data"]["required_balance_cents"] == _HTTP_500


def test_rate_limit_error_captures_retry_after(monkeypatch):
    monkeypatch.setattr(
        "src.common.time_utils.get_current_utc",
        lambda: datetime(2024, 1, 3, 12, 0, 0, tzinfo=timezone.utc),
    )

    err = KalshiRateLimitError(
        message="slow down",
        retry_after_seconds=7,
        operation_name="get_orders",
    )

    assert err.error_code == "RATE_LIMIT_EXCEEDED"
    assert err.retry_after_seconds == _TEST_COUNT_7
    assert err.request_data == {"retry_after_seconds": 7}
    assert err.to_dict()["operation_name"] == "get_orders"


def test_api_error_preserves_response_data(monkeypatch):
    monkeypatch.setattr(
        "src.common.time_utils.get_current_utc",
        lambda: datetime(2024, 1, 4, 12, 0, 0, tzinfo=timezone.utc),
    )

    response_payload = {"detail": "bad request"}
    err = KalshiAPIError(
        message="api failure",
        status_code=400,
        response_data=response_payload,
        operation_name="sync_orders",
    )

    assert err.error_code == "API_ERROR"
    assert err.status_code == _HTTP_400
    assert err.response_data is response_payload
    assert err.request_data == {
        "status_code": 400,
        "response_data": response_payload,
    }
    assert err.to_dict()["message"] == "api failure"


class TestKalshiAuthenticationError:
    """Tests for KalshiAuthenticationError."""

    def test_authentication_error_sets_correct_error_code(self, monkeypatch) -> None:
        """Authentication error sets AUTHENTICATION_FAILED code."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 5, 12, 0, 0, tzinfo=timezone.utc),
        )

        err = KalshiAuthenticationError(message="Invalid API key", operation_name="authenticate")

        assert err.error_code == "AUTHENTICATION_FAILED"
        assert err.operation_name == "authenticate"
        assert err.message == "Invalid API key"

    def test_authentication_error_inherits_from_trading_error(self) -> None:
        """KalshiAuthenticationError inherits from KalshiTradingError."""
        assert issubclass(KalshiAuthenticationError, KalshiTradingError)


class TestKalshiOrderValidationError:
    """Tests for KalshiOrderValidationError."""

    def test_order_validation_error_preserves_order_data(self, monkeypatch) -> None:
        """Order validation error preserves order data in request_data."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 6, 12, 0, 0, tzinfo=timezone.utc),
        )

        order_data = {"ticker": "INVALID", "price": 150}
        err = KalshiOrderValidationError(
            message="Price out of range",
            operation_name="validate_order",
            order_data=order_data,
        )

        assert err.error_code == "ORDER_VALIDATION_FAILED"
        assert err.request_data == order_data


class TestKalshiMarketClosedError:
    """Tests for KalshiMarketClosedError."""

    def test_market_closed_error_sets_ticker_and_status(self, monkeypatch) -> None:
        """Market closed error sets ticker and market_status."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 7, 12, 0, 0, tzinfo=timezone.utc),
        )

        err = KalshiMarketClosedError(
            message="Market is closed",
            ticker="TEST-MARKET",
            market_status="settled",
            operation_name="place_order",
        )

        assert err.error_code == "MARKET_CLOSED"
        assert err.ticker == "TEST-MARKET"
        assert err.market_status == "settled"
        assert err.request_data == {"ticker": "TEST-MARKET", "market_status": "settled"}


class TestKalshiOrderRejectedError:
    """Tests for KalshiOrderRejectedError."""

    def test_order_rejected_error_captures_rejection_reason(self, monkeypatch) -> None:
        """Order rejected error captures rejection reason."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 8, 12, 0, 0, tzinfo=timezone.utc),
        )

        order_data = {"ticker": "TEST", "price": 50}
        err = KalshiOrderRejectedError(
            message="Order rejected by exchange",
            rejection_reason="Price does not cross spread",
            operation_name="execute_order",
            order_data=order_data,
        )

        assert err.error_code == "ORDER_REJECTED"
        assert err.rejection_reason == "Price does not cross spread"
        assert err.request_data == order_data


class TestKalshiRateLimiterQueueFullError:
    """Tests for KalshiRateLimiterQueueFullError."""

    def test_rate_limiter_queue_full_error(self, monkeypatch) -> None:
        """Rate limiter queue full error sets queue info."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 9, 12, 0, 0, tzinfo=timezone.utc),
        )

        err = KalshiRateLimiterQueueFullError(
            message="Queue full",
            queue_type="read",
            queue_size=100,
            operation_name="get_orders",
        )

        assert err.error_code == "RATE_LIMITER_QUEUE_FULL"
        assert err.queue_type == "read"
        assert err.queue_size == 100
        assert err.request_data == {"queue_type": "read", "queue_size": 100}


class TestKalshiRateLimiterBugError:
    """Tests for KalshiRateLimiterBugError."""

    def test_rate_limiter_bug_error(self, monkeypatch) -> None:
        """Rate limiter bug error indicates implementation bug."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc),
        )

        request_data = {"endpoint": "/api/orders"}
        err = KalshiRateLimiterBugError(
            message="429 received despite rate limiting",
            operation_name="fetch_orders",
            request_data=request_data,
        )

        assert err.error_code == "RATE_LIMITER_BUG"
        assert err.request_data == request_data


class TestKalshiNetworkError:
    """Tests for KalshiNetworkError."""

    def test_network_error_captures_underlying_error(self, monkeypatch) -> None:
        """Network error captures underlying exception."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 11, 12, 0, 0, tzinfo=timezone.utc),
        )

        underlying = TimeoutError("Connection timed out")
        err = KalshiNetworkError(
            message="Network request failed",
            operation_name="connect",
            underlying_error=underlying,
        )

        assert err.error_code == "NETWORK_ERROR"
        assert err.underlying_error is underlying
        assert err.request_data == {"underlying_error": "Connection timed out"}

    def test_network_error_handles_none_underlying_error(self, monkeypatch) -> None:
        """Network error handles None underlying error."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 12, 12, 0, 0, tzinfo=timezone.utc),
        )

        err = KalshiNetworkError(
            message="Network request failed",
            operation_name="connect",
            underlying_error=None,
        )

        assert err.request_data == {"underlying_error": None}


class TestKalshiDataIntegrityError:
    """Tests for KalshiDataIntegrityError."""

    def test_data_integrity_error_captures_validation_errors(self, monkeypatch) -> None:
        """Data integrity error captures validation errors."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 13, 12, 0, 0, tzinfo=timezone.utc),
        )

        validation_errors = ["Missing field: price", "Invalid type: ticker"]
        data = {"ticker": 123}
        err = KalshiDataIntegrityError(
            message="Data validation failed",
            validation_errors=validation_errors,
            operation_name="parse_response",
            data=data,
        )

        assert err.error_code == "DATA_INTEGRITY_ERROR"
        assert err.validation_errors == validation_errors
        assert err.request_data == {"validation_errors": validation_errors, "invalid_data": data}

    def test_data_integrity_error_defaults_to_empty_list(self, monkeypatch) -> None:
        """Data integrity error defaults validation_errors to empty list."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 14, 12, 0, 0, tzinfo=timezone.utc),
        )

        err = KalshiDataIntegrityError(message="Data validation failed")

        assert err.validation_errors == []


class TestKalshiOrderNotFoundError:
    """Tests for KalshiOrderNotFoundError."""

    def test_order_not_found_error_captures_ids(self, monkeypatch) -> None:
        """Order not found error captures order and client IDs."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )

        err = KalshiOrderNotFoundError(
            message="Order not found",
            order_id="order-123",
            client_order_id="client-456",
            operation_name="get_order",
        )

        assert err.error_code == "ORDER_NOT_FOUND"
        assert err.order_id == "order-123"
        assert err.client_order_id == "client-456"
        assert err.request_data == {"order_id": "order-123", "client_order_id": "client-456"}


class TestKalshiPositionError:
    """Tests for KalshiPositionError."""

    def test_position_error_captures_ticker_and_data(self, monkeypatch) -> None:
        """Position error captures ticker and position data."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
        )

        position_data = {"quantity": 100, "average_price": 50}
        err = KalshiPositionError(
            message="Position calculation failed",
            ticker="TEST-MARKET",
            operation_name="calculate_position",
            position_data=position_data,
        )

        assert err.error_code == "POSITION_ERROR"
        assert err.ticker == "TEST-MARKET"
        assert err.request_data == {"ticker": "TEST-MARKET", "position_data": position_data}


class TestKalshiConfigurationError:
    """Tests for KalshiConfigurationError."""

    def test_configuration_error_captures_config_key(self, monkeypatch) -> None:
        """Configuration error captures config key."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 17, 12, 0, 0, tzinfo=timezone.utc),
        )

        err = KalshiConfigurationError(
            message="Missing configuration",
            config_key="API_KEY",
            operation_name="initialize",
        )

        assert err.error_code == "CONFIGURATION_ERROR"
        assert err.config_key == "API_KEY"
        assert err.request_data == {"config_key": "API_KEY"}


class TestKalshiOrderPollingError:
    """Tests for KalshiOrderPollingError."""

    def test_order_polling_error_captures_order_id(self, monkeypatch) -> None:
        """Order polling error captures order ID."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 18, 12, 0, 0, tzinfo=timezone.utc),
        )

        err = KalshiOrderPollingError(
            message="Polling timed out",
            order_id="order-123",
            operation_name="poll_order",
        )

        assert err.error_code == "ORDER_POLLING_FAILED"
        assert err.order_id == "order-123"
        assert err.request_data == {"order_id": "order-123"}

    def test_order_polling_error_merges_request_data(self, monkeypatch) -> None:
        """Order polling error merges additional request data."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 19, 12, 0, 0, tzinfo=timezone.utc),
        )

        extra_data = {"poll_count": 5, "timeout_seconds": 30}
        err = KalshiOrderPollingError(
            message="Polling timed out",
            order_id="order-123",
            operation_name="poll_order",
            request_data=extra_data,
        )

        assert err.request_data == {"order_id": "order-123", "poll_count": 5, "timeout_seconds": 30}


class TestKalshiTradePersistenceError:
    """Tests for KalshiTradePersistenceError."""

    def test_trade_persistence_error_captures_ids(self, monkeypatch) -> None:
        """Trade persistence error captures order ID and ticker."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 20, 12, 0, 0, tzinfo=timezone.utc),
        )

        err = KalshiTradePersistenceError(
            message="Failed to persist trade",
            order_id="order-123",
            ticker="TEST-MARKET",
            operation_name="persist_trade",
        )

        assert err.error_code == "TRADE_PERSISTENCE_FAILED"
        assert err.order_id == "order-123"
        assert err.ticker == "TEST-MARKET"
        assert err.request_data == {"order_id": "order-123", "ticker": "TEST-MARKET"}


class TestKalshiTradeNotificationError:
    """Tests for KalshiTradeNotificationError."""

    def test_trade_notification_error_captures_order_id(self, monkeypatch) -> None:
        """Trade notification error captures order ID."""
        monkeypatch.setattr(
            "src.common.time_utils.get_current_utc",
            lambda: datetime(2024, 1, 21, 12, 0, 0, tzinfo=timezone.utc),
        )

        err = KalshiTradeNotificationError(
            message="Failed to send notification",
            order_id="order-123",
            operation_name="notify_trade",
        )

        assert err.error_code == "TRADE_NOTIFICATION_FAILED"
        assert err.order_id == "order-123"
        assert err.request_data == {"order_id": "order-123"}


class TestTradingExceptionInheritance:
    """Tests for exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_trading_error(self) -> None:
        """All trading exceptions inherit from KalshiTradingError."""
        exception_classes = [
            KalshiAuthenticationError,
            KalshiOrderValidationError,
            KalshiInsufficientFundsError,
            KalshiMarketClosedError,
            KalshiOrderRejectedError,
            KalshiRateLimitError,
            KalshiRateLimiterQueueFullError,
            KalshiRateLimiterBugError,
            KalshiNetworkError,
            KalshiAPIError,
            KalshiDataIntegrityError,
            KalshiOrderNotFoundError,
            KalshiPositionError,
            KalshiConfigurationError,
            KalshiOrderPollingError,
            KalshiTradePersistenceError,
            KalshiTradeNotificationError,
        ]

        for exc_class in exception_classes:
            assert issubclass(
                exc_class, KalshiTradingError
            ), f"{exc_class.__name__} should inherit from KalshiTradingError"

    def test_all_exceptions_can_be_caught_as_exception(self) -> None:
        """All trading exceptions can be caught as base Exception."""
        exception_classes = [
            KalshiTradingError,
            KalshiAuthenticationError,
            KalshiOrderValidationError,
        ]

        for exc_class in exception_classes:
            assert issubclass(exc_class, Exception)
