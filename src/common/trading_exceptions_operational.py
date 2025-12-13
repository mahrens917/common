"""Operational Kalshi trading exceptions."""

from __future__ import annotations

from typing import Any, Dict, Optional

from common.truthy import pick_truthy

from .trading_exceptions_core import KalshiTradingError


class KalshiNetworkError(KalshiTradingError):
    """
    Network connectivity or timeout error.

    Raised when network requests fail due to connectivity issues, timeouts,
    or other network-related problems. This error should trigger retry logic.
    """

    def __init__(
        self,
        message: str,
        operation_name: Optional[str] = None,
        underlying_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            operation_name=operation_name,
            request_data={"underlying_error": str(underlying_error) if underlying_error else None},
        )
        self.underlying_error = underlying_error


class KalshiAPIError(KalshiTradingError):
    """
    General API error from Kalshi service.

    Raised when the API returns an error response that doesn't fit other specific categories.
    Contains HTTP status code and response details for debugging.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="API_ERROR",
            operation_name=operation_name,
            request_data={"status_code": status_code, "response_data": response_data},
        )
        self.status_code = status_code
        self.response_data = response_data


class KalshiDataIntegrityError(KalshiTradingError):
    """
    Data integrity validation failed.

    Raised when received data fails validation checks, such as:
    - Invalid data types
    - Missing required fields
    - Data consistency violations
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        operation_name: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="DATA_INTEGRITY_ERROR",
            operation_name=operation_name,
            request_data={"validation_errors": validation_errors, "invalid_data": data},
        )
        self.validation_errors = pick_truthy(validation_errors, [])


class KalshiOrderNotFoundError(KalshiTradingError):
    """
    Order not found in system.

    Raised when querying for an order that doesn't exist or is not accessible.
    This could indicate order ID mismatch or data synchronization issues.
    """

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        client_order_id: Optional[str] = None,
        operation_name: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="ORDER_NOT_FOUND",
            operation_name=operation_name,
            request_data={"order_id": order_id, "client_order_id": client_order_id},
        )
        self.order_id = order_id
        self.client_order_id = client_order_id


class KalshiPositionError(KalshiTradingError):
    """
    Position-related error.

    Raised when position operations fail, such as:
    - Position not found
    - Position calculation errors
    - Position limit violations
    """

    def __init__(
        self,
        message: str,
        ticker: Optional[str] = None,
        operation_name: Optional[str] = None,
        position_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="POSITION_ERROR",
            operation_name=operation_name,
            request_data={"ticker": ticker, "position_data": position_data},
        )
        self.ticker = ticker


class KalshiConfigurationError(KalshiTradingError):
    """
    Configuration or setup error.

    Raised when trading system configuration is invalid or incomplete, such as:
    - Missing environment variables
    - Invalid configuration parameters
    - Setup validation failures
    """

    def __init__(self, message: str, config_key: Optional[str] = None, operation_name: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            operation_name=operation_name,
            request_data={"config_key": config_key},
        )
        self.config_key = config_key


class KalshiOrderPollingError(KalshiTradingError):
    """
    Order polling failure.

    Raised when timeout orchestration, fill retrieval, or fill normalization fails.
    These failures should typically abort the execution flow so callers can react.
    """

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        operation_name: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
    ):
        request_payload = {"order_id": order_id}
        if request_data:
            request_payload.update(request_data)

        super().__init__(
            message=message,
            error_code="ORDER_POLLING_FAILED",
            operation_name=operation_name,
            request_data=request_payload,
        )
        self.order_id = order_id


class KalshiTradePersistenceError(KalshiTradingError):
    """
    Trade persistence failure.

    Raised when trade metadata validation or persistence into the trade store fails.
    """

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        ticker: Optional[str] = None,
        operation_name: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="TRADE_PERSISTENCE_FAILED",
            operation_name=operation_name,
            request_data={"order_id": order_id, "ticker": ticker},
        )
        self.order_id = order_id
        self.ticker = ticker


class KalshiTradeNotificationError(KalshiTradingError):
    """
    Trade notification failure.

    Raised when downstream notification systems fail to deliver trade updates.
    """

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        operation_name: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="TRADE_NOTIFICATION_FAILED",
            operation_name=operation_name,
            request_data={"order_id": order_id},
        )
        self.order_id = order_id
