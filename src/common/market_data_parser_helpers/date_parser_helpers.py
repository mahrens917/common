# ruff: noqa: PLR2004, PLR0913, PLR0911, PLR0912, PLR0915, C901
"""Helper functions for date parsing."""

import re
from datetime import datetime
from typing import Tuple

from ..market_data_parser import DateTimeCorruptionError, ParsingError

# Constants extracted for ruff PLR2004 compliance
YEAR_2DIGIT_ASSUME_50 = 50


def validate_date_format(date_part: str, pattern: re.Pattern) -> Tuple[str, str, str]:
    """
    Validate date format and extract components.

    Args:
        date_part: Date string to validate
        pattern: Compiled regex pattern

    Returns:
        Tuple of (day, month, year) strings

    Raises:
        ParsingError: If format is invalid
    """
    match = pattern.match(date_part)
    if not match:
        raise ParsingError(f"Invalid date format: {date_part}")
    day, month, year = match.groups()
    return day, month, year


def parse_year_component(year_str: str) -> int:
    """
    Convert 2-digit year to 4-digit year.

    Args:
        year_str: 2-digit year string

    Returns:
        4-digit year
    """
    year_2digit = int(year_str)
    if year_2digit < 50:  # Assume 00-49 means 2000-2049
        return 2000 + year_2digit
    # Assume 50-99 means 1950-1999 (unlikely for options)
    return 1900 + year_2digit


def validate_year_range(year: int, current_year: int) -> None:
    """
    Validate year is within reasonable range for options.

    Args:
        year: Year to validate
        current_year: Current year for comparison

    Raises:
        ParsingError: If year is outside valid range
    """
    if year < current_year or year > current_year + 10:
        raise ParsingError(
            f"Year {year} outside reasonable range ({current_year} to {current_year + 10})"
        )


def check_corruption(year: int, date_part: str) -> None:
    """
    Check for corrupted year values (2520/2620 bug).

    Args:
        year: Year value to check
        date_part: Original date string for error message

    Raises:
        DateTimeCorruptionError: If corrupted year detected
    """
    if year in [2520, 2620]:
        raise DateTimeCorruptionError(
            f"Detected corrupted year {year} from date_part '{date_part}'"
        )


def validate_datetime_corruption(parsed_date: datetime) -> None:
    """
    Final validation that datetime is not corrupted.

    Args:
        parsed_date: Parsed datetime to validate

    Raises:
        DateTimeCorruptionError: If corrupted datetime detected
    """
    if parsed_date.year in [2520, 2620]:
        raise DateTimeCorruptionError(f"Created corrupted datetime: {parsed_date}")
