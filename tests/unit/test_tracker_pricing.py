"""Tests for tracker_pricing module."""

import math

import pytest

from common.errors import PricingValidationError
from common.tracker_pricing import (
    _coerce_optional_price,
    _coerce_price,
    _normalize_numeric_string,
)


class TestNormalizeNumericString:
    """Tests for _normalize_numeric_string function."""

    def test_valid_integer(self) -> None:
        """Test valid integer string."""
        assert _normalize_numeric_string("123") == "123"

    def test_valid_decimal(self) -> None:
        """Test valid decimal string."""
        assert _normalize_numeric_string("123.45") == "123.45"

    def test_valid_negative(self) -> None:
        """Test valid negative number."""
        assert _normalize_numeric_string("-123.45") == "-123.45"

    def test_leading_plus(self) -> None:
        """Test leading plus is stripped."""
        assert _normalize_numeric_string("+123") == "123"

    def test_percentage_stripped(self) -> None:
        """Test percentage symbol is stripped."""
        assert _normalize_numeric_string("50%") == "50"

    def test_empty_string_returns_none(self) -> None:
        """Test empty string returns None."""
        assert _normalize_numeric_string("") is None

    def test_whitespace_only_returns_none(self) -> None:
        """Test whitespace only returns None."""
        assert _normalize_numeric_string("   ") is None

    def test_none_sentinel_returns_none(self) -> None:
        """Test 'none' sentinel returns None."""
        assert _normalize_numeric_string("none") is None

    def test_null_sentinel_returns_none(self) -> None:
        """Test 'null' sentinel returns None."""
        assert _normalize_numeric_string("null") is None

    def test_nan_sentinel_returns_none(self) -> None:
        """Test 'nan' sentinel returns None."""
        assert _normalize_numeric_string("nan") is None

    def test_non_numeric_returns_none(self) -> None:
        """Test non-numeric string returns None."""
        assert _normalize_numeric_string("abc") is None

    def test_percent_only_returns_none(self) -> None:
        """Test percent only returns None."""
        assert _normalize_numeric_string("%") is None

    def test_whitespace_trimmed(self) -> None:
        """Test whitespace is trimmed."""
        assert _normalize_numeric_string("  123  ") == "123"

    def test_decimal_starting_with_dot(self) -> None:
        """Test decimal starting with dot."""
        assert _normalize_numeric_string(".5") == ".5"


class TestCoercePrice:
    """Tests for _coerce_price function."""

    def test_valid_float(self) -> None:
        """Test valid float value."""
        assert _coerce_price(123.45) == 123.45

    def test_valid_int(self) -> None:
        """Test valid int value."""
        assert _coerce_price(100) == 100.0

    def test_valid_string(self) -> None:
        """Test valid string value."""
        assert _coerce_price("123.45") == 123.45

    def test_string_with_percent(self) -> None:
        """Test string with percent."""
        assert _coerce_price("50%") == 50.0

    def test_none_raises(self) -> None:
        """Test None raises error."""
        with pytest.raises(PricingValidationError):
            _coerce_price(None)

    def test_empty_string_raises(self) -> None:
        """Test empty string raises error."""
        with pytest.raises(PricingValidationError):
            _coerce_price("")

    def test_non_numeric_string_raises(self) -> None:
        """Test non-numeric string raises error."""
        with pytest.raises(PricingValidationError):
            _coerce_price("abc")

    def test_nan_string_raises(self) -> None:
        """Test 'nan' string raises error."""
        with pytest.raises(PricingValidationError):
            _coerce_price("nan")


class TestCoerceOptionalPrice:
    """Tests for _coerce_optional_price function."""

    def test_valid_float(self) -> None:
        """Test valid float value."""
        assert _coerce_optional_price(123.45) == 123.45

    def test_valid_int(self) -> None:
        """Test valid int value."""
        assert _coerce_optional_price(100) == 100.0

    def test_valid_string(self) -> None:
        """Test valid string value."""
        assert _coerce_optional_price("123.45") == 123.45

    def test_none_returns_none(self) -> None:
        """Test None returns None."""
        assert _coerce_optional_price(None) is None

    def test_empty_string_returns_none(self) -> None:
        """Test empty string returns None."""
        assert _coerce_optional_price("") is None

    def test_nan_sentinel_returns_none(self) -> None:
        """Test 'nan' sentinel returns None."""
        assert _coerce_optional_price("nan") is None

    def test_null_sentinel_returns_none(self) -> None:
        """Test 'null' sentinel returns None."""
        assert _coerce_optional_price("null") is None

    def test_nan_float_raises(self) -> None:
        """Test float NaN raises error."""
        with pytest.raises(PricingValidationError):
            _coerce_optional_price(float("nan"))

    def test_string_with_percent(self) -> None:
        """Test string with percent."""
        assert _coerce_optional_price("75%") == 75.0
