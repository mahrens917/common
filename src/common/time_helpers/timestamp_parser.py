from __future__ import annotations

"""Shared timestamp parsing helpers."""

import math
from datetime import datetime, timezone
from typing import Any

# Constants - magnitude thresholds for detecting timestamp units
MILLISECOND_TIMESTAMP_THRESHOLD = 1e12  # Above this = milliseconds
MICROSECOND_TIMESTAMP_THRESHOLD = 1e15  # Above this = microseconds
NANOSECOND_TIMESTAMP_THRESHOLD = 1e18  # Above this = nanoseconds


def parse_timestamp(value: Any, *, allow_none: bool = False) -> datetime | None:
    """
    Convert assorted timestamp inputs into an aware UTC datetime.

    Args:
        value: Timestamp-like input (iso string, epoch seconds/ms/us/ns, datetime, bytes).
        allow_none: When True, return None on missing/invalid input instead of raising.
    """
    if value is None:
        return _handle_none_value(allow_none)

    if isinstance(value, datetime):
        return _convert_datetime_to_utc(value)

    if isinstance(value, (bytes, bytearray)):
        return parse_timestamp(value.decode("utf-8", errors="ignore"), allow_none=allow_none)

    if isinstance(value, (int, float)):
        return _parse_numeric_timestamp(value, allow_none)

    if isinstance(value, str):
        return _parse_string_timestamp(value, allow_none)

    if allow_none:
        return None
    raise TypeError(f"Unsupported timestamp type: {type(value)}")


def _handle_none_value(allow_none: bool) -> datetime | None:
    """Handle None value based on allow_none flag."""
    if allow_none:
        return None
    raise ValueError("Timestamp value is required")


def _convert_datetime_to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC, adding timezone if naive."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_numeric_timestamp(value: int | float, allow_none: bool) -> datetime | None:
    """Parse numeric timestamp (seconds, milliseconds, microseconds, or nanoseconds)."""
    numeric = float(value)
    if not math.isfinite(numeric):
        if allow_none:
            return None
        raise ValueError(f"Non-finite timestamp value: {value!r}")
    # Detect unit based on magnitude and convert to seconds
    if numeric > NANOSECOND_TIMESTAMP_THRESHOLD:
        numeric /= 1_000_000_000.0  # nanoseconds to seconds
    elif numeric > MICROSECOND_TIMESTAMP_THRESHOLD:
        numeric /= 1_000_000.0  # microseconds to seconds
    elif numeric > MILLISECOND_TIMESTAMP_THRESHOLD:
        numeric /= 1000.0  # milliseconds to seconds
    return datetime.fromtimestamp(numeric, tz=timezone.utc)


def _parse_string_timestamp(value: str, allow_none: bool) -> datetime | None:
    """Parse ISO format string timestamp or numeric string."""
    token = value.strip()
    if not token:
        if allow_none:
            return None
        raise ValueError("Timestamp string cannot be empty")

    # Try to parse as numeric string first (epoch timestamp)
    try:
        numeric = float(token)
        if math.isfinite(numeric):
            return _parse_numeric_timestamp(numeric, allow_none)
    except ValueError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        pass  # Not a numeric string, try ISO format

    # Parse as ISO format
    try:
        normalized = token.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        if allow_none:
            return None
        raise
