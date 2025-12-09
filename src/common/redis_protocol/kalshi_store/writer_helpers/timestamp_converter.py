"""Timestamp conversion utilities - delegates to canonical implementation."""

from datetime import datetime
from typing import Optional

from src.common.time_helpers.timestamp_parser import parse_timestamp


def convert_string_timestamp(value: str) -> Optional[datetime]:
    """
    Convert string timestamp to datetime.

    Delegates to canonical parse_timestamp implementation.

    Args:
        value: String timestamp

    Returns:
        datetime or None if conversion fails
    """
    return parse_timestamp(value, allow_none=True)


def convert_numeric_timestamp(value: float) -> Optional[datetime]:
    """
    Convert numeric timestamp to datetime.

    Delegates to canonical parse_timestamp implementation.

    Args:
        value: Numeric timestamp

    Returns:
        datetime or None if conversion fails
    """
    return parse_timestamp(value, allow_none=True)
