"""Tests for kalshi_catalog_helpers.market_filter_helpers.close_time_validator module."""

from datetime import datetime, timezone

import pytest

from common.kalshi_catalog_helpers.market_filter_helpers.close_time_validator import (
    CloseTimeValidator,
)


class TestCloseTimeValidatorIsInFuture:
    """Tests for is_in_future method."""

    def test_future_close_time_timestamp(self) -> None:
        """Test market with future close time as timestamp."""
        now_ts = 1735000000.0  # Some reference time
        market = {"ticker": "KXTEST", "close_time": now_ts + 3600}  # 1 hour in future

        result = CloseTimeValidator.is_in_future(market, now_ts)

        assert result is True

    def test_past_close_time_timestamp(self) -> None:
        """Test market with past close time as timestamp."""
        now_ts = 1735000000.0
        market = {"ticker": "KXTEST", "close_time": now_ts - 3600}  # 1 hour in past

        result = CloseTimeValidator.is_in_future(market, now_ts)

        assert result is False

    def test_future_expiration_time_string(self) -> None:
        """Test market with future expiration time as ISO string."""
        now_ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        market = {
            "ticker": "KXTEST",
            "expected_expiration_time": "2025-01-01T18:00:00Z",
        }

        result = CloseTimeValidator.is_in_future(market, now_ts)

        assert result is True

    def test_checks_multiple_fields(self) -> None:
        """Test checks multiple close time fields."""
        now_ts = 1735000000.0
        market = {
            "ticker": "KXTEST",
            "close_time": None,  # Skip this
            "expiration_time": now_ts + 3600,  # Use this
        }

        result = CloseTimeValidator.is_in_future(market, now_ts)

        assert result is True

    def test_missing_all_timestamps(self) -> None:
        """Test returns False when all timestamps missing."""
        market = {"ticker": "KXTEST"}

        result = CloseTimeValidator.is_in_future(market, 1735000000.0)

        assert result is False

    def test_empty_string_timestamp(self) -> None:
        """Test skips empty string timestamps."""
        now_ts = 1735000000.0
        market = {
            "ticker": "KXTEST",
            "close_time": "",
            "expiration_time": now_ts + 3600,
        }

        result = CloseTimeValidator.is_in_future(market, now_ts)

        assert result is True


class TestCloseTimeValidatorParseCloseTime:
    """Tests for _parse_close_time method."""

    def test_parses_int(self) -> None:
        """Test parses integer timestamp."""
        result = CloseTimeValidator._parse_close_time(1735000000)

        assert result == 1735000000.0

    def test_parses_float(self) -> None:
        """Test parses float timestamp."""
        result = CloseTimeValidator._parse_close_time(1735000000.5)

        assert result == 1735000000.5

    def test_parses_iso_string(self) -> None:
        """Test parses ISO format string."""
        result = CloseTimeValidator._parse_close_time("2025-01-01T12:00:00+00:00")

        expected = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        assert result == expected

    def test_parses_iso_string_with_z(self) -> None:
        """Test parses ISO format string with Z suffix."""
        result = CloseTimeValidator._parse_close_time("2025-01-01T12:00:00Z")

        expected = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        assert result == expected

    def test_invalid_string_returns_none(self) -> None:
        """Test returns None for invalid string."""
        result = CloseTimeValidator._parse_close_time("not-a-date")

        assert result is None

    def test_unsupported_type_returns_none(self) -> None:
        """Test returns None for unsupported type."""
        result = CloseTimeValidator._parse_close_time(["list", "value"])

        assert result is None

    def test_none_returns_none(self) -> None:
        """Test returns None for None input."""
        result = CloseTimeValidator._parse_close_time(None)

        assert result is None
