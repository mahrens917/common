"""Timestamp normalization helpers."""

from datetime import datetime, timezone


class TimestampConverter:
    """Converts various timestamp formats to ISO8601."""

    # Threshold values for timestamp unit detection
    NANOSECOND_THRESHOLD = 1_000_000_000_000_000
    MICROSECOND_THRESHOLD = 1_000_000_000_000
    MILLISECOND_THRESHOLD = 1_000_000_000

    @staticmethod
    def normalize_string_timestamp(value: str) -> str:
        """Normalize string timestamp to ISO8601."""
        candidate = value
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        dt = datetime.fromisoformat(candidate)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()

    @staticmethod
    def normalize_numeric_timestamp(value: float) -> str:
        """Normalize numeric timestamp to ISO8601."""
        seconds = float(value)

        if seconds > TimestampConverter.NANOSECOND_THRESHOLD:
            seconds /= 1_000_000_000
        elif seconds > TimestampConverter.MICROSECOND_THRESHOLD:
            seconds /= 1_000_000
        elif seconds > TimestampConverter.MILLISECOND_THRESHOLD:
            seconds /= 1_000

        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        return dt.isoformat()
