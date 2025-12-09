"""Tests for spread validator module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.common.redis_protocol.atomic_redis_operations_helpers.spread_validator import (
    RedisDataValidationError,
    SpreadValidator,
)


class TestSpreadValidator:
    """Tests for SpreadValidator class."""

    def test_init_stores_max_retries(self) -> None:
        """Stores max_retries."""
        validator = SpreadValidator(max_retries=5)

        assert validator.max_retries == 5

    def test_init_sets_logger(self) -> None:
        """Sets logger."""
        validator = SpreadValidator(max_retries=3)

        assert validator.logger is not None


class TestValidateBidAskSpread:
    """Tests for validate_bid_ask_spread method."""

    def test_passes_when_spread_valid(self) -> None:
        """Passes when bid < ask."""
        validator = SpreadValidator(max_retries=3)
        data = {"best_bid": 100.0, "best_ask": 101.0}

        # Should not raise
        validator.validate_bid_ask_spread(data, "test:key", 0)

    def test_passes_when_no_bid_field(self) -> None:
        """Passes when best_bid not in data."""
        validator = SpreadValidator(max_retries=3)
        data = {"best_ask": 101.0}

        # Should not raise
        validator.validate_bid_ask_spread(data, "test:key", 0)

    def test_passes_when_no_ask_field(self) -> None:
        """Passes when best_ask not in data."""
        validator = SpreadValidator(max_retries=3)
        data = {"best_bid": 100.0}

        # Should not raise
        validator.validate_bid_ask_spread(data, "test:key", 0)

    def test_passes_when_no_bid_ask_fields(self) -> None:
        """Passes when neither bid nor ask in data."""
        validator = SpreadValidator(max_retries=3)
        data = {"other_field": "value"}

        # Should not raise
        validator.validate_bid_ask_spread(data, "test:key", 0)

    def test_raises_when_bid_greater_than_ask(self) -> None:
        """Raises RedisDataValidationError when bid > ask."""
        validator = SpreadValidator(max_retries=3)
        data = {"best_bid": 102.0, "best_ask": 100.0}

        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.validate_bid_ask_spread(data, "test:key", 0)

        assert "Invalid spread" in str(exc_info.value)
        assert "bid=102.0 > ask=100.0" in str(exc_info.value)

    def test_raises_when_bid_is_zero(self) -> None:
        """Raises RedisDataValidationError when bid is zero."""
        validator = SpreadValidator(max_retries=3)
        data = {"best_bid": 0.0, "best_ask": 100.0}

        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.validate_bid_ask_spread(data, "test:key", 0)

        assert "Invalid prices" in str(exc_info.value)
        assert "prices must be positive" in str(exc_info.value)

    def test_raises_when_ask_is_zero(self) -> None:
        """Raises RedisDataValidationError when ask is zero (triggers inverted spread)."""
        validator = SpreadValidator(max_retries=3)
        data = {"best_bid": 100.0, "best_ask": 0.0}

        # When ask=0 and bid=100, the inverted spread check (bid > ask) triggers first
        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.validate_bid_ask_spread(data, "test:key", 0)

        assert "Invalid spread" in str(exc_info.value)

    def test_raises_when_bid_is_negative(self) -> None:
        """Raises RedisDataValidationError when bid is negative."""
        validator = SpreadValidator(max_retries=3)
        data = {"best_bid": -10.0, "best_ask": 100.0}

        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.validate_bid_ask_spread(data, "test:key", 0)

        assert "Invalid prices" in str(exc_info.value)

    def test_raises_when_bid_is_not_numeric(self) -> None:
        """Raises RedisDataValidationError when bid is not numeric."""
        validator = SpreadValidator(max_retries=3)
        data = {"best_bid": "not_a_number", "best_ask": 100.0}

        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.validate_bid_ask_spread(data, "test:key", 0)

        assert "Error validating spread" in str(exc_info.value)

    def test_raises_when_ask_is_not_numeric(self) -> None:
        """Raises RedisDataValidationError when ask is not numeric."""
        validator = SpreadValidator(max_retries=3)
        data = {"best_bid": 100.0, "best_ask": "invalid"}

        with pytest.raises(RedisDataValidationError) as exc_info:
            validator.validate_bid_ask_spread(data, "test:key", 0)

        assert "Error validating spread" in str(exc_info.value)

    def test_logs_warning_on_inverted_spread(self) -> None:
        """Logs warning when spread is inverted."""
        validator = SpreadValidator(max_retries=3)
        validator.logger = MagicMock()
        data = {"best_bid": 102.0, "best_ask": 100.0}

        with pytest.raises(RedisDataValidationError):
            validator.validate_bid_ask_spread(data, "test:key", 1)

        validator.logger.warning.assert_called()
        call_args = validator.logger.warning.call_args
        # Check that diagnostic prefix and attempt numbers are in the args
        assert "ATOMIC_OPS_DIAGNOSTIC" in str(call_args)
        # attempt_index=1, so it shows as 2 (1+1)
        assert call_args[0][2] == 2  # attempt number
        assert call_args[0][3] == 3  # max retries

    def test_passes_string_numeric_values(self) -> None:
        """Passes when bid/ask are string representations of numbers."""
        validator = SpreadValidator(max_retries=3)
        data = {"best_bid": "99.5", "best_ask": "100.5"}

        # Should not raise - strings can be converted to float
        validator.validate_bid_ask_spread(data, "test:key", 0)


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
