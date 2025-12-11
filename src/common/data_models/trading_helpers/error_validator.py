"""Validation helpers for trading error data models."""

from datetime import datetime
from typing import Any

# Error messages
ERR_MISSING_ERROR_CODE = "Error code must be specified"
ERR_MISSING_ERROR_MESSAGE = "Error message must be specified"


def validate_error_code(error_code: str) -> None:
    """
    Validate error code is non-empty.

    Args:
        error_code: Error identifier code

    Raises:
        ValueError: If error code is empty
    """
    if not error_code:
        raise ValueError(ERR_MISSING_ERROR_CODE)


def validate_error_message(error_message: str) -> None:
    """
    Validate error message is non-empty.

    Args:
        error_message: Human-readable error description

    Raises:
        ValueError: If error message is empty
    """
    if not error_message:
        raise ValueError(ERR_MISSING_ERROR_MESSAGE)


def validate_operation_name(operation_name: str) -> None:
    """
    Validate operation name is non-empty.

    Args:
        operation_name: Name of failed operation

    Raises:
        ValueError: If operation name is empty
    """
    if not operation_name:
        raise ValueError("Operation name must be specified")


def validate_error_timestamp(timestamp: Any) -> None:
    """
    Validate error timestamp is datetime object.

    Args:
        timestamp: Error occurrence timestamp

    Raises:
        TypeError: If timestamp is not datetime
    """
    if not isinstance(timestamp, datetime):
        raise TypeError("Error timestamp must be a datetime object")


def validate_trading_error(error_code: str, error_message: str, operation_name: str, timestamp: datetime) -> None:
    """
    Validate complete trading error data.

    Args:
        error_code: Error identifier code
        error_message: Human-readable error description
        operation_name: Name of failed operation
        timestamp: Error occurrence timestamp

    Raises:
        ValueError: If any validation fails
    """
    validate_error_code(error_code)
    validate_error_message(error_message)
    validate_operation_name(operation_name)
    validate_error_timestamp(timestamp)
