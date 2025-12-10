"""Tests for date parser helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

from common.market_data_parser import DateTimeCorruptionError, ParsingError
from common.market_data_parser_helpers.date_parser_helpers import (
    check_corruption,
    parse_year_component,
    validate_date_format,
    validate_datetime_corruption,
    validate_year_range,
)


class TestValidateDateFormat:
    """Tests for validate_date_format function."""

    def test_extracts_date_components(self) -> None:
        """Extracts day, month, year from date string."""
        pattern = re.compile(r"(\d{2})([A-Z]{3})(\d{2})")

        day, month, year = validate_date_format("25JAN01", pattern)

        assert day == "25"
        assert month == "JAN"
        assert year == "01"

    def test_raises_on_invalid_format(self) -> None:
        """Raises ParsingError for invalid format."""
        pattern = re.compile(r"(\d{2})([A-Z]{3})(\d{2})")

        with pytest.raises(ParsingError, match="Invalid date format"):
            validate_date_format("INVALID", pattern)

    def test_raises_on_partial_match(self) -> None:
        """Raises ParsingError when pattern doesn't match at start."""
        pattern = re.compile(r"(\d{2})([A-Z]{3})(\d{2})")

        with pytest.raises(ParsingError, match="Invalid date format"):
            validate_date_format("X25JAN01", pattern)


class TestParseYearComponent:
    """Tests for parse_year_component function."""

    def test_converts_00_to_2000(self) -> None:
        """Converts 00 to 2000."""
        assert parse_year_component("00") == 2000

    def test_converts_01_to_2001(self) -> None:
        """Converts 01 to 2001."""
        assert parse_year_component("01") == 2001

    def test_converts_25_to_2025(self) -> None:
        """Converts 25 to 2025."""
        assert parse_year_component("25") == 2025

    def test_converts_49_to_2049(self) -> None:
        """Converts 49 to 2049."""
        assert parse_year_component("49") == 2049

    def test_converts_50_to_1950(self) -> None:
        """Converts 50 to 1950."""
        assert parse_year_component("50") == 1950

    def test_converts_99_to_1999(self) -> None:
        """Converts 99 to 1999."""
        assert parse_year_component("99") == 1999


class TestValidateYearRange:
    """Tests for validate_year_range function."""

    def test_accepts_current_year(self) -> None:
        """Accepts current year."""
        validate_year_range(2025, 2025)

    def test_accepts_year_plus_10(self) -> None:
        """Accepts year up to 10 years in future."""
        validate_year_range(2035, 2025)

    def test_rejects_year_before_current(self) -> None:
        """Rejects year before current."""
        with pytest.raises(ParsingError, match="outside reasonable range"):
            validate_year_range(2024, 2025)

    def test_rejects_year_more_than_10_years_ahead(self) -> None:
        """Rejects year more than 10 years ahead."""
        with pytest.raises(ParsingError, match="outside reasonable range"):
            validate_year_range(2036, 2025)


class TestCheckCorruption:
    """Tests for check_corruption function."""

    def test_raises_for_year_2520(self) -> None:
        """Raises DateTimeCorruptionError for 2520."""
        with pytest.raises(DateTimeCorruptionError, match="corrupted year 2520"):
            check_corruption(2520, "25JAN20")

    def test_raises_for_year_2620(self) -> None:
        """Raises DateTimeCorruptionError for 2620."""
        with pytest.raises(DateTimeCorruptionError, match="corrupted year 2620"):
            check_corruption(2620, "26JAN20")

    def test_accepts_normal_year(self) -> None:
        """Accepts normal year without raising."""
        check_corruption(2025, "25JAN25")

    def test_accepts_year_2525(self) -> None:
        """Accepts year 2525 (not corrupted)."""
        check_corruption(2525, "25JAN25")


class TestValidateDatetimeCorruption:
    """Tests for validate_datetime_corruption function."""

    def test_raises_for_datetime_with_year_2520(self) -> None:
        """Raises DateTimeCorruptionError for datetime with year 2520."""
        corrupted = datetime(2520, 1, 25, 8, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(DateTimeCorruptionError, match="corrupted datetime"):
            validate_datetime_corruption(corrupted)

    def test_raises_for_datetime_with_year_2620(self) -> None:
        """Raises DateTimeCorruptionError for datetime with year 2620."""
        corrupted = datetime(2620, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(DateTimeCorruptionError, match="corrupted datetime"):
            validate_datetime_corruption(corrupted)

    def test_accepts_normal_datetime(self) -> None:
        """Accepts normal datetime without raising."""
        normal = datetime(2025, 1, 25, 8, 0, 0, tzinfo=timezone.utc)

        validate_datetime_corruption(normal)

    def test_accepts_far_future_datetime(self) -> None:
        """Accepts far future datetime (not specifically corrupted)."""
        future = datetime(2525, 1, 25, 8, 0, 0, tzinfo=timezone.utc)

        validate_datetime_corruption(future)
