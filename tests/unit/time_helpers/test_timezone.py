"""
Tests for src/common/time_helpers/timezone.py

Tests timezone and clock helper functions.
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytz

from common.time_helpers.timezone import (
    ensure_timezone_aware,
    format_datetime,
    format_timestamp,
    get_current_date_in_timezone,
    get_current_est,
    get_current_utc,
    get_days_ago_utc,
    get_start_of_day_utc,
    get_timezone_aware_date,
    load_configured_timezone,
    sleep_until_next_minute,
    to_utc,
    validate_timezone,
)


class TestGetCurrentUtc:
    """Tests for get_current_utc() function."""

    def test_returns_timezone_aware_utc_datetime(self):
        """get_current_utc() returns timezone-aware UTC datetime."""
        result = get_current_utc()

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc


class TestValidateTimezone:
    """Tests for validate_timezone() function."""

    def test_returns_true_for_valid_timezone(self):
        """validate_timezone() returns True for valid timezone."""
        assert validate_timezone("UTC") is True
        assert validate_timezone("America/New_York") is True

    def test_returns_false_for_invalid_timezone(self):
        """validate_timezone() returns False for invalid timezone."""
        assert validate_timezone("Invalid/Timezone") is False


class TestEnsureTimezoneAware:
    """Tests for ensure_timezone_aware() function."""

    def test_adds_utc_to_naive_datetime(self):
        """ensure_timezone_aware() adds UTC to naive datetime."""
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        result = ensure_timezone_aware(naive_dt)

        assert result.tzinfo == timezone.utc

    def test_raises_on_unsupported_type(self):
        """ensure_timezone_aware() raises TypeError on unsupported type."""
        with pytest.raises(TypeError, match="Unsupported datetime value type"):
            ensure_timezone_aware(123)

    def test_parses_iso_string(self):
        """ensure_timezone_aware() parses ISO format string."""
        result = ensure_timezone_aware("2024-01-01T12:00:00Z")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None


class TestGetCurrentEst:
    """Tests for get_current_est() function."""

    def test_returns_eastern_timezone_datetime(self):
        """get_current_est() returns US/Eastern timezone datetime."""
        result = get_current_est()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None


class TestGetCurrentTime:
    """Tests for get_current_time() function."""

    def test_raises_on_invalid_timezone(self):
        """get_current_time() raises ValueError on invalid timezone."""
        with pytest.raises(ValueError, match="Unknown timezone"):
            from common.time_helpers.timezone import get_current_time

            get_current_time("Invalid/Timezone")


class TestToUtc:
    """Tests for to_utc() function."""

    def test_converts_aware_datetime_to_utc(self):
        """to_utc() converts timezone-aware datetime to UTC."""
        est = pytz.timezone("US/Eastern")
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=est)
        result = to_utc(dt)
        assert result.tzinfo == timezone.utc

    def test_adds_utc_to_naive_datetime(self):
        """to_utc() adds UTC to naive datetime."""
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        result = to_utc(naive_dt)
        assert result.tzinfo == timezone.utc


class TestGetStartOfDayUtc:
    """Tests for get_start_of_day_utc() function."""

    def test_returns_start_of_day_utc(self):
        """get_start_of_day_utc() returns start of day in UTC."""
        dt = datetime(2024, 1, 1, 15, 30, 45, tzinfo=timezone.utc)
        result = get_start_of_day_utc(dt)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0


class TestGetDaysAgoUtc:
    """Tests for get_days_ago_utc() function."""

    def test_returns_datetime_days_ago(self):
        """get_days_ago_utc() returns datetime N days ago."""
        result = get_days_ago_utc(7)
        now = get_current_utc()
        assert isinstance(result, datetime)
        assert result < now


class TestFormatTimestamp:
    """Tests for format_timestamp() function."""

    def test_formats_datetime_with_timezone(self):
        """format_timestamp() formats datetime with timezone."""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = format_timestamp(dt, "UTC")
        assert "2024-01-01" in result
        assert "UTC" in result

    def test_formats_int_timestamp(self):
        """format_timestamp() formats integer timestamp."""
        timestamp = 1704110400
        result = format_timestamp(timestamp, "UTC")
        assert "UTC" in result

    def test_raises_on_invalid_timezone(self):
        """format_timestamp() raises ValueError on invalid timezone."""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="Unknown timezone"):
            format_timestamp(dt, "Invalid/Timezone")


class TestSleepUntilNextMinute:
    """Tests for sleep_until_next_minute() function."""

    @pytest.mark.asyncio
    async def test_sleeps_until_next_minute(self):
        """sleep_until_next_minute() suspends until next minute."""
        with patch("common.time_helpers.timezone.asyncio.sleep") as mock_sleep:
            await sleep_until_next_minute()
            mock_sleep.assert_called_once()
            sleep_duration = mock_sleep.call_args[0][0]
            assert 0 < sleep_duration <= 60
