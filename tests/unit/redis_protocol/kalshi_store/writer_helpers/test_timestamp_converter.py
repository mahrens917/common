"""Tests for timestamp converter module."""

from datetime import datetime, timezone

from src.common.redis_protocol.kalshi_store.writer_helpers.timestamp_converter import (
    convert_numeric_timestamp,
    convert_string_timestamp,
)


class TestConvertStringTimestamp:
    """Tests for convert_string_timestamp function."""

    def test_convert_iso_format(self) -> None:
        """Converts ISO format timestamp."""
        result = convert_string_timestamp("2024-12-01T12:00:00")

        assert result is not None
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 1
        assert result.hour == 12

    def test_convert_iso_format_with_z(self) -> None:
        """Converts ISO format with Z suffix."""
        result = convert_string_timestamp("2024-12-01T12:00:00Z")

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_convert_iso_format_with_timezone(self) -> None:
        """Converts ISO format with timezone offset."""
        result = convert_string_timestamp("2024-12-01T12:00:00+00:00")

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_convert_returns_none_for_invalid(self) -> None:
        """Returns None for invalid string."""
        result = convert_string_timestamp("not a timestamp")

        assert result is None

    def test_convert_returns_none_for_empty(self) -> None:
        """Returns None for empty string."""
        result = convert_string_timestamp("")

        assert result is None


class TestConvertNumericTimestamp:
    """Tests for convert_numeric_timestamp function."""

    def test_convert_seconds_timestamp(self) -> None:
        """Converts timestamp in seconds."""
        result = convert_numeric_timestamp(1733054400.0)

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_convert_milliseconds_timestamp(self) -> None:
        """Converts timestamp in milliseconds."""
        result = convert_numeric_timestamp(1733054400000.0)

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_convert_microseconds_timestamp(self) -> None:
        """Converts timestamp in microseconds."""
        result = convert_numeric_timestamp(1733054400000000.0)

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_convert_nanoseconds_timestamp(self) -> None:
        """Converts timestamp in nanoseconds."""
        result = convert_numeric_timestamp(1733054400000000000.0)

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_convert_returns_none_for_non_numeric_string(self) -> None:
        """Returns None when passed non-numeric that can't be converted."""
        result = convert_numeric_timestamp(float("nan"))

        assert result is None
