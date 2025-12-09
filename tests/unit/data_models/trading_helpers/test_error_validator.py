"""Tests for error validator module."""

from datetime import datetime

import pytest

from src.common.data_models.trading_helpers.error_validator import (
    ERR_MISSING_ERROR_CODE,
    ERR_MISSING_ERROR_MESSAGE,
    validate_error_code,
    validate_error_message,
    validate_error_timestamp,
    validate_operation_name,
    validate_trading_error,
)


class TestValidateErrorCode:
    """Tests for validate_error_code function."""

    def test_valid_code(self) -> None:
        """Accepts valid error code."""
        validate_error_code("RATE_LIMIT_EXCEEDED")

    def test_empty_code_raises(self) -> None:
        """Raises ValueError for empty code."""
        with pytest.raises(ValueError) as exc_info:
            validate_error_code("")

        assert ERR_MISSING_ERROR_CODE in str(exc_info.value)


class TestValidateErrorMessage:
    """Tests for validate_error_message function."""

    def test_valid_message(self) -> None:
        """Accepts valid error message."""
        validate_error_message("Rate limit exceeded, please retry")

    def test_empty_message_raises(self) -> None:
        """Raises ValueError for empty message."""
        with pytest.raises(ValueError) as exc_info:
            validate_error_message("")

        assert ERR_MISSING_ERROR_MESSAGE in str(exc_info.value)


class TestValidateOperationName:
    """Tests for validate_operation_name function."""

    def test_valid_operation(self) -> None:
        """Accepts valid operation name."""
        validate_operation_name("place_order")

    def test_empty_operation_raises(self) -> None:
        """Raises ValueError for empty operation."""
        with pytest.raises(ValueError) as exc_info:
            validate_operation_name("")

        assert "Operation name must be specified" in str(exc_info.value)


class TestValidateErrorTimestamp:
    """Tests for validate_error_timestamp function."""

    def test_valid_timestamp(self) -> None:
        """Accepts valid datetime."""
        validate_error_timestamp(datetime.now())

    def test_string_raises(self) -> None:
        """Raises TypeError for string."""
        with pytest.raises(TypeError) as exc_info:
            validate_error_timestamp("2024-01-01")

        assert "datetime object" in str(exc_info.value)


class TestValidateTradingError:
    """Tests for validate_trading_error function."""

    def test_valid_complete_error(self) -> None:
        """Accepts valid complete trading error."""
        validate_trading_error(
            error_code="RATE_LIMIT",
            error_message="Too many requests",
            operation_name="place_order",
            timestamp=datetime.now(),
        )

    def test_invalid_code_propagates(self) -> None:
        """Propagates error code validation error."""
        with pytest.raises(ValueError) as exc_info:
            validate_trading_error(
                error_code="",
                error_message="Too many requests",
                operation_name="place_order",
                timestamp=datetime.now(),
            )

        assert "Error code" in str(exc_info.value)

    def test_invalid_message_propagates(self) -> None:
        """Propagates error message validation error."""
        with pytest.raises(ValueError) as exc_info:
            validate_trading_error(
                error_code="RATE_LIMIT",
                error_message="",
                operation_name="place_order",
                timestamp=datetime.now(),
            )

        assert "Error message" in str(exc_info.value)

    def test_invalid_operation_propagates(self) -> None:
        """Propagates operation name validation error."""
        with pytest.raises(ValueError) as exc_info:
            validate_trading_error(
                error_code="RATE_LIMIT",
                error_message="Too many requests",
                operation_name="",
                timestamp=datetime.now(),
            )

        assert "Operation name" in str(exc_info.value)

    def test_invalid_timestamp_propagates(self) -> None:
        """Propagates timestamp validation error."""
        with pytest.raises(TypeError):
            validate_trading_error(
                error_code="RATE_LIMIT",
                error_message="Too many requests",
                operation_name="place_order",
                timestamp="2024-01-01",
            )
