"""Tests for common error types."""

import pytest

from common.errors import PricingValidationError


class TestPricingValidationError:
    """Tests for PricingValidationError exception."""

    def test_init_with_default_reason(self) -> None:
        """Test PricingValidationError initialization with default reason."""
        error = PricingValidationError("invalid_value")
        assert error.value == "invalid_value"
        assert error.reason == "Invalid numeric value"
        assert str(error) == "Invalid numeric value: invalid_value"

    def test_init_with_custom_reason(self) -> None:
        """Test PricingValidationError initialization with custom reason."""
        error = PricingValidationError("bad_price", reason="Price out of bounds")
        assert error.value == "bad_price"
        assert error.reason == "Price out of bounds"
        assert str(error) == "Price out of bounds: bad_price"

    def test_is_value_error(self) -> None:
        """Test that PricingValidationError is a ValueError."""
        error = PricingValidationError("test")
        assert isinstance(error, ValueError)
