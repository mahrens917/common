"""Common exception classes for the application.

All custom exceptions should inherit from these base classes to maintain
a consistent exception hierarchy across the codebase.

Exception classes support two patterns:
1. No-argument raise: raise ConfigurationError()
2. Contextual attributes: err = ConfigurationError(field="x", value=123); raise err
"""

from typing import Any


class ApplicationError(Exception):
    """Base exception for all application errors.

    Supports keyword arguments that are stored as attributes for debugging.
    """

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            message = self.__class__.__doc__ or "Application error occurred"
        super().__init__(message)
        for key, value in kwargs.items():
            setattr(self, key, value)


class ConfigurationError(ApplicationError):
    """Configuration is invalid or missing."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            message = "Configuration is invalid or missing"
        super().__init__(message, **kwargs)


class ValidationError(ApplicationError):
    """Data validation failed."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            message = "Data validation failed"
        super().__init__(message, **kwargs)


class DataError(ApplicationError):
    """Data processing or parsing error."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            message = "Data processing or parsing error"
        super().__init__(message, **kwargs)


class NetworkError(ApplicationError):
    """Network communication error."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            message = "Network communication error"
        super().__init__(message, **kwargs)


class RedisError(ApplicationError):
    """Redis operation error."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            message = "Redis operation error"
        super().__init__(message, **kwargs)


class APIError(ApplicationError):
    """External API error."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            message = "External API error"
        super().__init__(message, **kwargs)


class InvalidMarketDataError(ApplicationError):
    """Specific market data payload failed validation."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            message = "Market data payload failed validation"
        super().__init__(message, **kwargs)


class MessageHandlerError(ApplicationError):
    """Generic message handler failure."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            message = "Message handler failure"
        super().__init__(message, **kwargs)
