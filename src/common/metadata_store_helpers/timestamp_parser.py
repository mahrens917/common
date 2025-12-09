"""Timestamp parsing for history data."""

from typing import Optional

from src.common.time_helpers.timestamp_parser import parse_timestamp


def parse_history_timestamp(datetime_str: str) -> Optional[int]:
    """
    Parse timestamp string from history data.

    Delegates to canonical implementation in src.common.time_helpers.timestamp_parser.

    Args:
        datetime_str: Timestamp string

    Returns:
        Unix timestamp or None if parsing fails
    """
    try:
        dt = parse_timestamp(datetime_str, allow_none=True)
        if dt is None:
            return None
        return int(dt.timestamp())
    except (ValueError, TypeError):
        # Return None for invalid formats (preserves original behavior)
        return None
