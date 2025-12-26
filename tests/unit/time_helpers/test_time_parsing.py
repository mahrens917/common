"""Tests for time_helpers.time_parsing module."""

import pytest

from common.time_helpers.time_parsing import parse_time_utc


class TestParseTimeUtc:
    """Tests for parse_time_utc function."""

    def test_valid_hh_mm(self) -> None:
        """Test parsing valid HH:MM format."""
        result = parse_time_utc("14:30")
        assert result == (14, 30, 0)

    def test_valid_hh_mm_ss(self) -> None:
        """Test parsing valid HH:MM:SS format."""
        result = parse_time_utc("08:15:45")
        assert result == (8, 15, 45)

    def test_midnight(self) -> None:
        """Test parsing midnight."""
        result = parse_time_utc("00:00:00")
        assert result == (0, 0, 0)

    def test_end_of_day(self) -> None:
        """Test parsing 23:59:59."""
        result = parse_time_utc("23:59:59")
        assert result == (23, 59, 59)

    def test_leading_zeros(self) -> None:
        """Test parsing with leading zeros."""
        result = parse_time_utc("08:05:09")
        assert result == (8, 5, 9)

    def test_strips_whitespace(self) -> None:
        """Test strips leading/trailing whitespace."""
        result = parse_time_utc("  14:30  ")
        assert result == (14, 30, 0)

    def test_invalid_format_single_part(self) -> None:
        """Test raises error for single part."""
        with pytest.raises(ValueError, match="Invalid time string"):
            parse_time_utc("1430")

    def test_invalid_format_too_many_parts(self) -> None:
        """Test raises error for too many parts."""
        with pytest.raises(ValueError, match="Invalid time string"):
            parse_time_utc("14:30:00:00")

    def test_non_numeric_hour(self) -> None:
        """Test raises error for non-numeric hour."""
        with pytest.raises(ValueError, match="Non-numeric time component"):
            parse_time_utc("ab:30")

    def test_non_numeric_minute(self) -> None:
        """Test raises error for non-numeric minute."""
        with pytest.raises(ValueError, match="Non-numeric time component"):
            parse_time_utc("14:xy")

    def test_non_numeric_second(self) -> None:
        """Test raises error for non-numeric second."""
        with pytest.raises(ValueError, match="Non-numeric time component"):
            parse_time_utc("14:30:zz")

    def test_hour_out_of_range_high(self) -> None:
        """Test raises error for hour > 23."""
        with pytest.raises(ValueError, match="Time components out of range"):
            parse_time_utc("24:00")

    def test_hour_out_of_range_low(self) -> None:
        """Test raises error for negative hour."""
        with pytest.raises(ValueError, match="Time components out of range"):
            parse_time_utc("-1:00")

    def test_minute_out_of_range(self) -> None:
        """Test raises error for minute > 59."""
        with pytest.raises(ValueError, match="Time components out of range"):
            parse_time_utc("14:60")

    def test_second_out_of_range(self) -> None:
        """Test raises error for second > 59."""
        with pytest.raises(ValueError, match="Time components out of range"):
            parse_time_utc("14:30:60")

    def test_empty_string(self) -> None:
        """Test raises error for empty string."""
        with pytest.raises(ValueError, match="Invalid time string"):
            parse_time_utc("")

    def test_only_whitespace(self) -> None:
        """Test raises error for only whitespace."""
        with pytest.raises(ValueError, match="Invalid time string"):
            parse_time_utc("   ")
