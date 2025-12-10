"""Timestamp conversion helpers for Redis message serialization - delegates to canonical."""

from typing import Union

from common.exceptions import DataError
from common.time_helpers.timestamp_parser import parse_timestamp


def parse_utc_timestamp(value: Union[str, int, float]) -> int:
    """
    Parse ISO-8601 timestamps or numeric seconds into epoch seconds.

    Delegates to canonical parse_timestamp implementation.

    Args:
        value: String timestamp, or numeric seconds/milliseconds since epoch

    Returns:
        Integer timestamp (seconds since epoch)

    Raises:
        DataError: If timestamp cannot be parsed
    """
    try:
        dt = parse_timestamp(value, allow_none=False)
        assert dt is not None
        return int(dt.timestamp())
    except (ValueError, TypeError) as e:
        raise DataError(
            f"FAIL-FAST: Invalid timestamp format '{value}'. Cannot parse timestamp: {e}"
        ) from e


def format_utc_timestamp(timestamp: Union[int, float]) -> str:
    """
    Format integer timestamp to UTC string.

    Delegates to canonical parse_timestamp for normalization.

    Args:
        timestamp: Integer timestamp (seconds since epoch or milliseconds)

    Returns:
        Formatted timestamp string (ISO-8601 with Z suffix)
    """
    dt = parse_timestamp(timestamp, allow_none=False)
    assert dt is not None
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
