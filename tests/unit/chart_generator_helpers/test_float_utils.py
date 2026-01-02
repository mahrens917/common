"""Tests for chart_generator_helpers.float_utils module."""

import logging
from typing import Optional
from unittest.mock import patch

import pytest

from common.chart_generator_helpers.float_utils import safe_float

# Test constants (data_guard requirement)
TEST_VALID_FLOAT_STRING: str = "3.14159"
TEST_VALID_FLOAT_VALUE: float = 3.14159
TEST_INVALID_STRING: str = "not_a_number"
TEST_EMPTY_STRING: str = ""
TEST_NAN_STRING: str = "nan"
TEST_INF_STRING: str = "inf"
TEST_ZERO_STRING: str = "0.0"
TEST_ZERO_VALUE: float = 0.0
TEST_NEGATIVE_FLOAT_STRING: str = "-42.5"
TEST_NEGATIVE_FLOAT_VALUE: float = -42.5


class TestSafeFloat:
    """Test cases for safe_float function."""

    def test_none_returns_none(self) -> None:
        """Test that None value returns None."""
        result: Optional[float] = safe_float(None)
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        """Test that empty string returns None."""
        result: Optional[float] = safe_float(TEST_EMPTY_STRING)
        assert result is None

    def test_valid_float_string_returns_float(self) -> None:
        """Test that valid float string is parsed correctly."""
        result: Optional[float] = safe_float(TEST_VALID_FLOAT_STRING)
        assert result == TEST_VALID_FLOAT_VALUE

    def test_invalid_string_returns_none(self) -> None:
        """Test that invalid string raises ValueError and returns None."""
        result: Optional[float] = safe_float(TEST_INVALID_STRING)
        assert result is None

    def test_zero_string_returns_zero(self) -> None:
        """Test that zero string is parsed correctly."""
        result: Optional[float] = safe_float(TEST_ZERO_STRING)
        assert result == TEST_ZERO_VALUE

    def test_negative_float_string_returns_negative_float(self) -> None:
        """Test that negative float string is parsed correctly."""
        result: Optional[float] = safe_float(TEST_NEGATIVE_FLOAT_STRING)
        assert result == TEST_NEGATIVE_FLOAT_VALUE

    def test_nan_string_returns_none(self) -> None:
        """Test that NaN string is rejected (allow_nan_inf=False)."""
        result: Optional[float] = safe_float(TEST_NAN_STRING)
        assert result is None

    def test_inf_string_returns_none(self) -> None:
        """Test that infinity string is rejected (allow_nan_inf=False)."""
        result: Optional[float] = safe_float(TEST_INF_STRING)
        assert result is None

    def test_value_error_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that ValueError causes warning log."""
        with caplog.at_level(logging.WARNING):
            result: Optional[float] = safe_float(TEST_INVALID_STRING)
            assert result is None
            assert "Failed to parse float" in caplog.text

    def test_safe_float_parse_called_with_correct_params(self) -> None:
        """Test that safe_float_parse is called with allow_nan_inf=False."""
        with patch("common.chart_generator_helpers.float_utils.safe_float_parse") as mock_parse:
            mock_parse.return_value = TEST_VALID_FLOAT_VALUE
            result: Optional[float] = safe_float(TEST_VALID_FLOAT_STRING)
            assert result == TEST_VALID_FLOAT_VALUE
            mock_parse.assert_called_once_with(TEST_VALID_FLOAT_STRING, allow_nan_inf=False)

    def test_safe_float_parse_raises_value_error(self) -> None:
        """Test that ValueError from safe_float_parse is caught and None returned."""
        with patch("common.chart_generator_helpers.float_utils.safe_float_parse") as mock_parse:
            mock_parse.side_effect = ValueError("Test error")
            result: Optional[float] = safe_float(TEST_VALID_FLOAT_STRING)
            assert result is None
