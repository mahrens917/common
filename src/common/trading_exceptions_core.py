"""
Custom exception classes for Kalshi trading operations.

This module provides specific exception types for different trading failure scenarios,
enabling precise error handling and monitoring. All exceptions follow fail-fast principles
with clear error messages and context preservation.
"""

from typing import Any, Dict, Optional


class KalshiTradingError(Exception):
    """
    Base exception for all Kalshi trading operations.

    Provides common functionality for error tracking, logging, and monitoring integration.
    All trading-specific exceptions inherit from this base class.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        operation_name: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize trading error with context information.

        Args:
            message: Human-readable error description
            error_code: Machine-readable error code for monitoring
            operation_name: Name of the operation that failed
            request_data: Request data that caused the error (for debugging)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.operation_name = operation_name
        self.request_data = request_data
        from .time_utils import get_current_utc

        self.timestamp = get_current_utc()

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and monitoring"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "operation_name": self.operation_name,
            "timestamp": self.timestamp.isoformat(),
            "request_data": self.request_data,
        }


class KalshiAuthenticationError(KalshiTradingError):
    """
    Authentication failed for trading operations.

    Raised when API key validation, signature verification, or token refresh fails.
    This error typically requires manual intervention to resolve credential issues.
    """

    def __init__(self, message: str, operation_name: Optional[str] = None):
        super().__init__(message=message, error_code="AUTHENTICATION_FAILED", operation_name=operation_name)


class KalshiOrderValidationError(KalshiTradingError):
    """
    Order parameters failed validation checks.

    Raised when order parameters are invalid, such as:
    - Invalid ticker format
    - Price outside valid range (1-99 cents)
    - Invalid quantity
    - Market not open for trading
    """

    def __init__(
        self,
        message: str,
        operation_name: Optional[str] = None,
        order_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="ORDER_VALIDATION_FAILED",
            operation_name=operation_name,
            request_data=order_data,
        )


class KalshiInsufficientFundsError(KalshiTradingError):
    """
    Insufficient account balance for order execution.

    Raised when attempting to place an order that exceeds available account balance.
    This error should trigger balance checks and potentially halt trading operations.
    """

    def __init__(
        self,
        message: str,
        required_balance_cents: Optional[int] = None,
        available_balance_cents: Optional[int] = None,
        operation_name: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_FUNDS",
            operation_name=operation_name,
            request_data={
                "required_balance_cents": required_balance_cents,
                "available_balance_cents": available_balance_cents,
            },
        )
        self.required_balance_cents = required_balance_cents
        self.available_balance_cents = available_balance_cents


class KalshiMarketClosedError(KalshiTradingError):
    """
    Market is not open for trading.

    Raised when attempting to trade on a market that is closed, settled, or suspended.
    This error should trigger market status checks before retrying.
    """

    def __init__(
        self,
        message: str,
        ticker: Optional[str] = None,
        market_status: Optional[str] = None,
        operation_name: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="MARKET_CLOSED",
            operation_name=operation_name,
            request_data={"ticker": ticker, "market_status": market_status},
        )
        self.ticker = ticker
        self.market_status = market_status


class KalshiOrderRejectedError(KalshiTradingError):
    """
    Order was rejected by the exchange.

    Raised when the exchange rejects an order for reasons such as:
    - Price does not cross the spread
    - Market conditions changed
    - Risk management limits exceeded
    """

    def __init__(
        self,
        message: str,
        rejection_reason: Optional[str] = None,
        operation_name: Optional[str] = None,
        order_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="ORDER_REJECTED",
            operation_name=operation_name,
            request_data=order_data,
        )
        self.rejection_reason = rejection_reason


class KalshiRateLimitError(KalshiTradingError):
    """
    API rate limit exceeded.

    Raised when too many requests are made in a short time period.
    This error should trigger exponential backoff retry logic.
    """

    def __init__(
        self,
        message: str,
        retry_after_seconds: Optional[int] = None,
        operation_name: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            operation_name=operation_name,
            request_data={"retry_after_seconds": retry_after_seconds},
        )
        self.retry_after_seconds = retry_after_seconds


class KalshiRateLimiterQueueFullError(KalshiTradingError):
    """
    Rate limiter queue is full - system overloaded.

    Raised when the rate limiter request queue has reached maximum capacity,
    indicating that the system is receiving more requests than it can process
    within the rate limits. This is a fail-fast error that should trigger
    immediate system load reduction or alerting.
    """

    def __init__(
        self,
        message: str,
        queue_type: Optional[str] = None,
        queue_size: Optional[int] = None,
        operation_name: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="RATE_LIMITER_QUEUE_FULL",
            operation_name=operation_name,
            request_data={"queue_type": queue_type, "queue_size": queue_size},
        )
        self.queue_type = queue_type
        self.queue_size = queue_size


class KalshiRateLimiterBugError(KalshiTradingError):
    """
    429 response received despite rate limiting - indicates rate limiter bug.

    Raised when the API returns a 429 rate limit response even though the
    rate limiter should have prevented this. This indicates a bug in the
    rate limiter implementation that must be fixed immediately.
    """

    def __init__(
        self,
        message: str,
        operation_name: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="RATE_LIMITER_BUG",
            operation_name=operation_name,
            request_data=request_data,
        )


class HTTPRequestError(KalshiTradingError):
    """
    HTTP request failed.

    Raised when an HTTP request fails due to network issues, timeouts,
    or other transport-level errors. This error indicates the request
    could not be completed and should be retried or reported.
    """

    def __init__(
        self,
        message: str,
        operation_name: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="HTTP_REQUEST_FAILED",
            operation_name=operation_name,
            request_data=request_data,
        )


class SessionNotConnectedError(KalshiTradingError):
    """
    Session is not connected.

    Raised when attempting to make a request without an active session.
    This error indicates the connection must be established before
    making requests.
    """

    def __init__(
        self,
        message: str,
        operation_name: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="SESSION_NOT_CONNECTED",
            operation_name=operation_name,
        )
