"""Tests for field validator module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from common.redis_protocol.atomic_redis_operations_helpers.field_validator import (
    FieldValidator,
    RedisDataValidationError,
)


class TestFieldValidator:
    """Tests for FieldValidator class."""

    def test_init_stores_max_retries(self) -> None:
        """Stores max_retries."""
        validator = FieldValidator(max_retries=5)

        assert validator.max_retries == 5

    def test_init_sets_logger(self) -> None:
        """Sets logger."""
        validator = FieldValidator(max_retries=3)

        assert validator.logger is not None


class TestEnsureRequiredFields:
    """Tests for ensure_required_fields method."""

    def test_passes_when_all_fields_present(self) -> None:
        """Passes when all required fields are present."""
        validator = FieldValidator(max_retries=3)
        data = {"field1": "value1", "field2": "value2", "field3": "value3"}
        required = ["field1", "field2"]

        # Should not raise
        validator.ensure_required_fields(data, required, "test:key", 0)

    def test_passes_when_no_required_fields(self) -> None:
        """Passes when no fields are required."""
        validator = FieldValidator(max_retries=3)
        data = {"field1": "value1"}
        required = []

        # Should not raise
        validator.ensure_required_fields(data, required, "test:key", 0)

    def test_raises_when_field_missing(self) -> None:
        """Raises RedisDataValidationError when field missing."""
        validator = FieldValidator(max_retries=3)
        data = {"field1": "value1"}
        required = ["field1", "field2"]

        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.ensure_required_fields(data, required, "test:key", 0)

        assert "Missing required fields" in str(exc_info.value)
        assert "field2" in str(exc_info.value)

    def test_raises_when_multiple_fields_missing(self) -> None:
        """Raises with all missing fields listed."""
        validator = FieldValidator(max_retries=3)
        data = {"field1": "value1"}
        required = ["field1", "field2", "field3"]

        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.ensure_required_fields(data, required, "test:key", 0)

        assert "field2" in str(exc_info.value)
        assert "field3" in str(exc_info.value)

    def test_raises_when_all_fields_missing(self) -> None:
        """Raises when all required fields are missing."""
        validator = FieldValidator(max_retries=3)
        data = {}
        required = ["field1", "field2"]

        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.ensure_required_fields(data, required, "test:key", 0)

        assert "field1" in str(exc_info.value)
        assert "field2" in str(exc_info.value)

    def test_includes_available_fields_in_error(self) -> None:
        """Includes available fields in error message."""
        validator = FieldValidator(max_retries=3)
        data = {"available1": "value", "available2": "value"}
        required = ["missing_field"]

        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.ensure_required_fields(data, required, "test:key", 0)

        assert "Available fields" in str(exc_info.value)
        assert "available1" in str(exc_info.value)
        assert "available2" in str(exc_info.value)

    def test_includes_key_in_error(self) -> None:
        """Includes store key in error message."""
        validator = FieldValidator(max_retries=3)
        data = {}
        required = ["field1"]

        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.ensure_required_fields(data, required, "markets:kalshi:btc", 0)

        assert "markets:kalshi:btc" in str(exc_info.value)

    def test_logs_warning_on_missing_fields(self) -> None:
        """Logs warning when fields are missing."""
        validator = FieldValidator(max_retries=3)
        validator.logger = MagicMock()
        data = {"field1": "value1"}
        required = ["field1", "field2"]

        with pytest.raises(RedisDataValidationError):
            validator.ensure_required_fields(data, required, "test:key", 1)

        validator.logger.warning.assert_called()
        call_args = validator.logger.warning.call_args
        # Check that diagnostic prefix and attempt numbers are in the args
        assert "ATOMIC_OPS_DIAGNOSTIC" in str(call_args)
        # attempt_index=1, so it shows as 2 (1+1)
        assert call_args[0][2] == 2  # attempt number
        assert call_args[0][3] == 3  # max retries

    def test_works_with_tuple_required_fields(self) -> None:
        """Works with tuple of required fields."""
        validator = FieldValidator(max_retries=3)
        data = {"field1": "value1", "field2": "value2"}
        required = ("field1", "field2")

        # Should not raise
        validator.ensure_required_fields(data, required, "test:key", 0)

    def test_works_with_none_values(self) -> None:
        """Passes when field present but value is None."""
        validator = FieldValidator(max_retries=3)
        data = {"field1": None}
        required = ["field1"]

        # Should not raise - field is present, value doesn't matter
        validator.ensure_required_fields(data, required, "test:key", 0)


class TestRedisDataValidationError:
    """Tests for RedisDataValidationError exception."""

    def test_is_runtime_error(self) -> None:
        """Is a RuntimeError subclass."""
        assert issubclass(RedisDataValidationError, RuntimeError)

    def test_can_be_raised_with_message(self) -> None:
        """Can be raised with a message."""
        with pytest.raises(RedisDataValidationError) as exc_info:
            raise RedisDataValidationError("test message")

        assert "test message" in str(exc_info.value)
