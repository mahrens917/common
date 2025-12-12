"""Date parsing helpers for Deribit instruments."""

import re
from datetime import datetime, timezone
from typing import Any

from ..market_data_parser import DateTimeCorruptionError, ParsingError

MONTH_MAP = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

DATE_PATTERN = re.compile(r"^(\d{1,2})([A-Z]{3})(\d{2})$")


# Constants
_CONST_50 = 50


class DeribitDateParser:
    """Handles Deribit date format parsing."""

    @classmethod
    def parse_date(cls, date_part: str) -> datetime:
        """
        Parse Deribit date format (e.g., '8JUN25', '26DEC25') to datetime.

        This method specifically prevents the datetime corruption bug that creates
        years 2520/2620 by properly handling 2-digit years.

        Args:
            date_part: Deribit date string

        Returns:
            datetime: Parsed date with 8am UTC (Deribit standard)

        Raises:
            ParsingError: If date format is invalid
            DateTimeCorruptionError: If parsing would create corrupted years
        """
        cleaned_part = _normalize_input(date_part)
        day_str, month_str, year_str = _extract_components(cleaned_part)
        day = _parse_day(day_str, cleaned_part)
        month = _parse_month(month_str)
        year = _resolve_year(year_str, cleaned_part)
        _validate_year_range(year, cleaned_part)
        parsed_date = datetime(year, month, day, 8, 0, 0, tzinfo=timezone.utc)
        _guard_against_corruption(parsed_date, cleaned_part)
        return parsed_date


def _normalize_input(date_part: Any) -> str:
    if not date_part or not isinstance(date_part, str):
        raise ParsingError(f"Invalid date part: {date_part}")
    cleaned_part = date_part.strip().upper()
    if not DATE_PATTERN.match(cleaned_part):
        raise ParsingError(f"Invalid date format: {cleaned_part}")
    return cleaned_part


def _extract_components(date_part: str) -> tuple[str, str, str]:
    match = DATE_PATTERN.match(date_part)
    if not match:
        raise ParsingError(f"Invalid date format: {date_part}")
    day_str, month_str, year_str = match.groups()
    return day_str, month_str, year_str


def _parse_day(day_str: str, date_part: str) -> int:
    try:
        return int(day_str)
    except (ValueError, TypeError) as exc:  # policy_guard: allow-silent-handler
        raise ParsingError(f"Invalid day in {date_part}") from exc


def _parse_month(month_str: str) -> int:
    month = MONTH_MAP.get(month_str)
    if month is None:
        raise ParsingError(f"Invalid month: {month_str}")
    return month


def _resolve_year(year_str: str, date_part: str) -> int:
    try:
        year_2digit = int(year_str)
    except (ValueError, TypeError) as exc:  # policy_guard: allow-silent-handler
        raise ParsingError(f"Invalid year in {date_part}") from exc

    if year_2digit < _CONST_50:
        return 2000 + year_2digit
    return 1900 + year_2digit


def _validate_year_range(year: int, date_part: str) -> None:
    from ..time_utils import get_current_utc

    current_year = get_current_utc().year
    max_year = current_year + 10
    if year < current_year or year > max_year:
        raise ParsingError(f"Year {year} outside reasonable range ({current_year} to {max_year})")


def _guard_against_corruption(parsed_date: datetime, date_part: str) -> None:
    if parsed_date.year in [2520, 2620]:
        raise DateTimeCorruptionError(f"Detected corrupted datetime from '{date_part}'")
