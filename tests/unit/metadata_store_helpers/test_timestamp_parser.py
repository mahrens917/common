"""Tests for timestamp parser."""

from __future__ import annotations

from src.common.metadata_store_helpers.timestamp_parser import parse_history_timestamp


class TestParseHistoryTimestamp:
    """Tests for parse_history_timestamp function."""

    def test_parses_iso_format_with_timezone(self) -> None:
        """parse_history_timestamp parses ISO format with timezone."""
        result = parse_history_timestamp("2025-01-01T12:00:00+00:00")
        assert result is not None
        assert isinstance(result, int)
        assert result > 0

    def test_parses_basic_datetime_format(self) -> None:
        """parse_history_timestamp parses basic datetime format."""
        result = parse_history_timestamp("2025-01-01 12:00:00")
        assert result is not None
        assert isinstance(result, int)
        assert result > 0

    def test_returns_none_for_invalid_format(self) -> None:
        """parse_history_timestamp returns None for invalid format."""
        result = parse_history_timestamp("not a date")
        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        """parse_history_timestamp returns None for empty string."""
        result = parse_history_timestamp("")
        assert result is None

    def test_parses_date_only_format(self) -> None:
        """parse_history_timestamp parses date-only format (delegates to canonical parser)."""
        result = parse_history_timestamp("2025-01-01")
        assert result is not None
        assert isinstance(result, int)

    def test_handles_type_error(self) -> None:
        """parse_history_timestamp handles None input gracefully."""
        # The function expects a string, but if given None will raise TypeError
        # which is caught and returns None
        result = parse_history_timestamp(None)  # type: ignore[arg-type]
        assert result is None

    def test_parses_iso_format_with_positive_offset(self) -> None:
        """parse_history_timestamp parses ISO format with positive offset."""
        result = parse_history_timestamp("2025-01-01T12:00:00+05:30")
        assert result is not None
        assert isinstance(result, int)

    def test_parses_iso_format_with_negative_offset(self) -> None:
        """parse_history_timestamp parses ISO format with negative offset (delegates to canonical parser)."""
        result = parse_history_timestamp("2025-01-01T12:00:00-08:00")
        assert result is not None
        assert isinstance(result, int)

    def test_parses_iso_format_without_timezone(self) -> None:
        """parse_history_timestamp parses ISO format without timezone (delegates to canonical parser)."""
        result = parse_history_timestamp("2025-01-01T12:00:00")
        assert result is not None
        assert isinstance(result, int)

    def test_basic_format_midnight(self) -> None:
        """parse_history_timestamp handles midnight in basic format."""
        result = parse_history_timestamp("2025-01-01 00:00:00")
        assert result is not None
        assert isinstance(result, int)

    def test_basic_format_end_of_day(self) -> None:
        """parse_history_timestamp handles end of day in basic format."""
        result = parse_history_timestamp("2025-01-01 23:59:59")
        assert result is not None
        assert isinstance(result, int)
