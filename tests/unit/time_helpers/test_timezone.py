"""
Tests for src/common/time_helpers/timezone.py

Tests timezone and clock helper functions.
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytz

from src.common.time_helpers.timezone import (
    ensure_timezone_aware,
    format_datetime,
    format_timestamp,
    get_current_date_in_timezone,
    get_current_est,
    get_current_time,
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
