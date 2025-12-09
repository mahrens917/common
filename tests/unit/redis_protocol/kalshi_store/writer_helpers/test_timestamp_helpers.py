"""Tests for timestamp helpers module."""

from src.common.redis_protocol.kalshi_store.writer_helpers.timestamp_helpers import (
    TimestampConverter,
)


class TestTimestampConverterNormalizeStringTimestamp:
    """Tests for TimestampConverter.normalize_string_timestamp."""

    def test_normalize_iso_format(self) -> None:
        """Normalizes ISO format timestamp."""
        result = TimestampConverter.normalize_string_timestamp("2024-12-01T12:00:00")

        assert "2024-12-01" in result
        assert "12:00:00" in result

    def test_normalize_z_suffix(self) -> None:
        """Handles Z suffix correctly."""
        result = TimestampConverter.normalize_string_timestamp("2024-12-01T12:00:00Z")

        assert "+00:00" in result or "Z" not in result

    def test_normalize_with_timezone(self) -> None:
        """Handles timezone offset correctly."""
        result = TimestampConverter.normalize_string_timestamp("2024-12-01T12:00:00+00:00")

        assert "2024-12-01" in result


class TestTimestampConverterNormalizeNumericTimestamp:
    """Tests for TimestampConverter.normalize_numeric_timestamp."""

    def test_normalize_seconds(self) -> None:
        """Normalizes seconds timestamp."""
        result = TimestampConverter.normalize_numeric_timestamp(1733054400.0)

        assert isinstance(result, str)
        assert "T" in result

    def test_normalize_milliseconds(self) -> None:
        """Normalizes milliseconds timestamp."""
        result = TimestampConverter.normalize_numeric_timestamp(1733054400000.0)

        assert isinstance(result, str)

    def test_normalize_microseconds(self) -> None:
        """Normalizes microseconds timestamp."""
        result = TimestampConverter.normalize_numeric_timestamp(1733054400000000.0)

        assert isinstance(result, str)

    def test_normalize_nanoseconds(self) -> None:
        """Normalizes nanoseconds timestamp."""
        result = TimestampConverter.normalize_numeric_timestamp(1733054400000000000.0)

        assert isinstance(result, str)


class TestTimestampConverterThresholds:
    """Tests for TimestampConverter threshold constants."""

    def test_nanosecond_threshold(self) -> None:
        """Nanosecond threshold is correct."""
        assert TimestampConverter.NANOSECOND_THRESHOLD == 1_000_000_000_000_000

    def test_microsecond_threshold(self) -> None:
        """Microsecond threshold is correct."""
        assert TimestampConverter.MICROSECOND_THRESHOLD == 1_000_000_000_000

    def test_millisecond_threshold(self) -> None:
        """Millisecond threshold is correct."""
        assert TimestampConverter.MILLISECOND_THRESHOLD == 1_000_000_000
