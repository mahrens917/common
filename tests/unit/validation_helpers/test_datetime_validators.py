"""Tests for datetime_validators module."""

from datetime import datetime, timezone

import pytest

from common.validation_helpers.datetime_validators import DatetimeValidators
from common.validation_helpers.exceptions import ValidationError


class TestValidateDatetimeObject:
    """Tests for validate_datetime_object method."""

    def test_valid_datetime_utc(self) -> None:
        """Test valid datetime with UTC timezone."""
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert DatetimeValidators.validate_datetime_object(dt) is True

    def test_valid_datetime_naive(self) -> None:
        """Test valid naive datetime."""
        dt = datetime(2024, 6, 15, 12, 0, 0)
        assert DatetimeValidators.validate_datetime_object(dt) is True

    def test_none_raises(self) -> None:
        """Test None datetime raises error."""
        with pytest.raises(ValidationError, match="cannot be None"):
            DatetimeValidators.validate_datetime_object(None)

    def test_non_datetime_raises(self) -> None:
        """Test non-datetime raises TypeError."""
        with pytest.raises(TypeError, match="must be datetime"):
            DatetimeValidators.validate_datetime_object("2024-06-15")

    def test_too_far_in_past_raises(self) -> None:
        """Test datetime before 1970 raises error."""
        dt = datetime(1960, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValidationError, match="too far in the past"):
            DatetimeValidators.validate_datetime_object(dt)

    def test_too_far_in_future_raises(self) -> None:
        """Test datetime after 2100 raises error."""
        dt = datetime(2150, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValidationError, match="too far in the future"):
            DatetimeValidators.validate_datetime_object(dt)

    def test_edge_case_1970(self) -> None:
        """Test datetime at 1970 boundary is valid."""
        dt = datetime(1970, 1, 2, tzinfo=timezone.utc)
        assert DatetimeValidators.validate_datetime_object(dt) is True

    def test_edge_case_2099(self) -> None:
        """Test datetime before 2100 is valid."""
        dt = datetime(2099, 12, 31, tzinfo=timezone.utc)
        assert DatetimeValidators.validate_datetime_object(dt) is True

    def test_custom_field_name_in_error(self) -> None:
        """Test custom field name appears in error."""
        with pytest.raises(ValidationError, match="expiry_date"):
            DatetimeValidators.validate_datetime_object(None, "expiry_date")


class TestValidateTimeToExpiry:
    """Tests for validate_time_to_expiry method."""

    def test_valid_time_to_expiry(self) -> None:
        """Test valid time to expiry."""
        assert DatetimeValidators.validate_time_to_expiry(1.5) is True

    def test_valid_small_time_to_expiry(self) -> None:
        """Test small positive time to expiry is valid."""
        assert DatetimeValidators.validate_time_to_expiry(0.001) is True

    def test_nan_raises(self) -> None:
        """Test NaN time to expiry raises error."""
        with pytest.raises(ValidationError, match="cannot be NaN"):
            DatetimeValidators.validate_time_to_expiry(float("nan"))

    def test_inf_raises(self) -> None:
        """Test infinite time to expiry raises error."""
        with pytest.raises(ValidationError, match="cannot be infinite"):
            DatetimeValidators.validate_time_to_expiry(float("inf"))

    def test_zero_raises(self) -> None:
        """Test zero time to expiry raises error."""
        with pytest.raises(ValidationError, match="must be positive"):
            DatetimeValidators.validate_time_to_expiry(0.0)

    def test_negative_raises(self) -> None:
        """Test negative time to expiry raises error."""
        with pytest.raises(ValidationError, match="must be positive"):
            DatetimeValidators.validate_time_to_expiry(-1.0)

    def test_exceeds_max_raises(self) -> None:
        """Test time to expiry exceeding max raises error."""
        with pytest.raises(ValidationError, match="exceeds maximum"):
            DatetimeValidators.validate_time_to_expiry(15.0)

    def test_at_max_is_valid(self) -> None:
        """Test time to expiry at max is valid."""
        assert DatetimeValidators.validate_time_to_expiry(10.0) is True

    def test_non_numeric_raises(self) -> None:
        """Test non-numeric raises TypeError."""
        with pytest.raises(TypeError, match="must be numeric"):
            DatetimeValidators.validate_time_to_expiry("1.5")
