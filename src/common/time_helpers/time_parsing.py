"""
Canonical time parsing utilities.

This module provides standardized functions for parsing time strings.
All time parsing implementations across the codebase should delegate to these functions.
"""

# Constants
MAX_HOUR = 23
MAX_MINUTE = 59
MAX_SECOND = 59
TIME_PARTS_WITH_SECONDS = 3

# Error messages
INVALID_TIME_STRING_ERROR_TEMPLATE = "Invalid time string '{}'"
NONNUMERIC_TIME_COMPONENT_ERROR_TEMPLATE = "Non-numeric time component in '{}'"
TIME_COMPONENTS_OUT_OF_RANGE_ERROR_TEMPLATE = "Time components out of range in '{}'"


def parse_time_utc(value: str) -> tuple[int, int, int]:
    """
    Parse a time string in HH:MM[:SS] format into hour, minute, second components.

    Args:
        value: Time string in format "HH:MM" or "HH:MM:SS"

    Returns:
        Tuple of (hour, minute, second) as integers

    Raises:
        ValueError: If the time string is invalid, contains non-numeric components,
                    or has out-of-range values

    Examples:
        >>> parse_time_utc("14:30")
        (14, 30, 0)
        >>> parse_time_utc("08:15:45")
        (8, 15, 45)
        >>> parse_time_utc("25:00")  # Raises ValueError
    """
    parts = value.strip().split(":")
    if len(parts) not in (2, 3):
        raise ValueError(INVALID_TIME_STRING_ERROR_TEMPLATE.format(value))

    try:
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) == TIME_PARTS_WITH_SECONDS else 0
    except ValueError as exc:
        raise ValueError(NONNUMERIC_TIME_COMPONENT_ERROR_TEMPLATE.format(value)) from exc

    if not (0 <= hour <= MAX_HOUR and 0 <= minute <= MAX_MINUTE and 0 <= second <= MAX_SECOND):
        raise ValueError(TIME_COMPONENTS_OUT_OF_RANGE_ERROR_TEMPLATE.format(value))

    return hour, minute, second


__all__ = ["parse_time_utc"]
