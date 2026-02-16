"""Common exception classes for the application.

All custom exceptions should inherit from these base classes to maintain
a consistent exception hierarchy across the codebase.

Exception classes support two patterns:
1. No-argument raise: raise ConfigurationError()
2. Contextual attributes: err = ConfigurationError(field="x", value=123); raise err
"""

from __future__ import annotations

from typing import Any, Tuple

_DEFAULT_APPLICATION_ERROR_MESSAGE = "Application error occurred"


class ApplicationError(Exception):
    """Base exception for all application errors.

    Supports keyword arguments that are stored as attributes for debugging.
    """

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            class_doc = self.__class__.__doc__
            message = class_doc if class_doc else _DEFAULT_APPLICATION_ERROR_MESSAGE
        super().__init__(message)
        for key, value in kwargs.items():
            setattr(self, key, value)


def _split_field_path(path: str) -> Tuple[str, str]:
    """Split a dotted field path into (section, field) for error messages."""
    if "." in path:
        parts = path.rsplit(".", 1)
        return parts[0], parts[1]
    return path, "value"


class ConfigurationError(ApplicationError):
    """Configuration is invalid or missing."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        if not message:
            message = "Configuration is invalid or missing"
        super().__init__(message, **kwargs)

    @classmethod
    def missing_section(cls, section: str) -> "ConfigurationError":
        """Create error for a missing configuration section."""
        return cls(f"Runtime configuration is invalid: missing '{section}' section")

    @classmethod
    def missing_field(cls, section: str, field: str) -> "ConfigurationError":
        """Create error for a missing field within a section."""
        return cls(f"Runtime configuration is invalid: missing '{section}.{field}' field")

    @classmethod
    def invalid_field(cls, section: str, field: str, reason: str) -> "ConfigurationError":
        """Create error for an invalid field value."""
        return cls(f"Runtime configuration is invalid: invalid '{section}.{field}' field ({reason})")

    @classmethod
    def missing_field_path(cls, path: str) -> "ConfigurationError":
        """Create error for a missing field using a dotted path."""
        section, field = _split_field_path(path)
        return cls.missing_field(section, field)

    @classmethod
    def invalid_field_path(cls, path: str, reason: str) -> "ConfigurationError":
        """Create error for an invalid field using a dotted path."""
        section, field = _split_field_path(path)
        return cls.invalid_field(section, field, reason)

    @classmethod
    def missing_key(cls, *, source: str, key: str) -> "ConfigurationError":
        """Create error for a missing key in a source."""
        return cls(f"Runtime configuration is invalid: {source} missing '{key}' key")


class ConfigurationTypeError(TypeError):
    """Raised when configuration payloads have unexpected types."""

    def __init__(self, *, section: str, expected: str) -> None:
        message = f"runtime config value '{section}' must be a {expected}"
        super().__init__(message)

    @classmethod
    def for_field(cls, path: str, expected: str) -> "ConfigurationTypeError":
        """Create type error for a field at the given path."""
        return cls(section=path, expected=expected)


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
