"""Core conversion utilities for expiry and epoch time."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

__all__ = [
    "parse_expiry_datetime",
    "validate_expiry_hour",
    "calculate_time_to_expiry_years",
    "compute_days_to_expiry",
    "get_time_from_epoch",
    "get_datetime_from_time_point",
    "parse_iso_datetime",
    "get_fixed_time_point",
    "format_time_key",
    "is_market_expired",
    "resolve_expiry_to_datetime",
]

EPOCH_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
DERIBIT_EXPIRY_HOUR = 8  # 08:00 UTC

_PRE_EPOCH_CLAMP_LOGGED = False


def parse_expiry_datetime(expiry: Any) -> datetime:
    """
    Parse an expiry value into a timezone-aware datetime.

    Supports strings, bytes, and datetime instances. Naive datetimes are assumed
    to be UTC for consistency across consumers.
    """
    from dateutil import parser as dateutil_parser

    candidate = expiry
    if isinstance(candidate, (bytes, bytearray)):
        candidate = candidate.decode("utf-8", "ignore")

    if isinstance(candidate, datetime):
        dt = candidate
    else:
        if candidate is None:
            raise ValueError("Expiry value missing")
        text = str(candidate)
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            dt = dateutil_parser.parse(text)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def validate_expiry_hour(expiry_dt: datetime, expected_hour: Optional[int] = None) -> bool:
    """Validate expiry hour matches expected value if provided."""
    if expected_hour is not None and expiry_dt.hour != expected_hour:
        logger.warning(
            "Unexpected expiry hour: %02d:00 (expected %02d:00)",
            expiry_dt.hour,
            expected_hour,
        )
        return False
    return True


def calculate_time_to_expiry_years(current_time: datetime, expiry_time: datetime) -> float:
    """Calculate time to expiry in years between two datetime objects."""
    delta = expiry_time - current_time
    return delta.total_seconds() / (365.25 * 24 * 3600)


def compute_days_to_expiry(expiry: Optional[datetime], now: datetime) -> Optional[int]:
    """
    Compute days to expiry from datetime.

    Returns ceiling of days remaining, or 0 if expired. Returns None if expiry is None.

    Args:
        expiry: Expiry datetime (timezone-aware recommended)
        now: Current datetime for comparison

    Returns:
        Days until expiry (ceiling), 0 if expired, None if expiry is None
    """
    import math

    if expiry is None:
        return None

    delta = expiry - now
    if delta.total_seconds() <= 0:
        return 0

    return int(math.ceil(delta.total_seconds() / 86400))


def get_time_from_epoch(expiry_dt: datetime) -> float:
    """Get time in years from epoch to expiry, clamping expiries before the epoch."""
    # Access _PRE_EPOCH_CLAMP_LOGGED through the module to support monkeypatching
    import sys

    expiry_module = sys.modules.get("common.time_helpers.expiry")
    if expiry_module and hasattr(expiry_module, "_PRE_EPOCH_CLAMP_LOGGED"):
        clamp_logged = getattr(expiry_module, "_PRE_EPOCH_CLAMP_LOGGED")
    else:
        clamp_logged = globals()["_PRE_EPOCH_CLAMP_LOGGED"]

    if expiry_dt < EPOCH_START:
        if not clamp_logged:
            logger.warning(
                "Expiry %s is before epoch %s; clamping to the epoch boundary",
                expiry_dt.isoformat(),
                EPOCH_START.isoformat(),
            )
            # Update the flag in the correct location
            if expiry_module and hasattr(expiry_module, "_PRE_EPOCH_CLAMP_LOGGED"):
                setattr(expiry_module, "_PRE_EPOCH_CLAMP_LOGGED", True)
            else:
                globals()["_PRE_EPOCH_CLAMP_LOGGED"] = True
        expiry_dt = EPOCH_START

    delta = expiry_dt - EPOCH_START
    return delta.total_seconds() / (365.25 * 24 * 3600)


def get_datetime_from_time_point(time_point: float) -> datetime:
    """Convert a time point (years from epoch) to a datetime object."""
    seconds = time_point * 365.25 * 24 * 3600
    return EPOCH_START + timedelta(seconds=seconds)


def parse_iso_datetime(expiry: str) -> Optional[Tuple[datetime, float]]:
    """
    Parse ISO 8601 formatted expiry strings into UTC datetimes and epoch offsets.

    Only accepts strict ISO 8601 format. Rejects deprecated Kalshi token formats
    like "28FEB25", "01JAN25", etc.
    """
    try:
        # Replace 'Z' suffix with explicit UTC offset
        text = expiry
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")

        # Use fromisoformat for strict ISO 8601 parsing
        expiry_dt = datetime.fromisoformat(text)

        # Ensure timezone-aware
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)

    except (ValueError, TypeError):
        logger.exception("Failed to parse ISO expiry %s", expiry)
        return None

    time_point = get_time_from_epoch(expiry_dt)
    expiry_dt = max(expiry_dt, EPOCH_START)

    return expiry_dt, time_point


def get_fixed_time_point(expiry: str) -> Optional[float]:
    """Calculate fixed time point based on expiry time."""
    result = parse_iso_datetime(expiry)
    return None if result is None else result[1]


def format_time_key(time_point: Optional[float]) -> Optional[str]:
    """Format time point as a consistent string key."""
    if time_point is None:
        return None
    return f"{time_point:.6f}"


def resolve_expiry_to_datetime(expiry: Any, *, instrument_name: Optional[str] = None) -> datetime:
    """
    Resolve expiry value to timezone-aware datetime.

    Handles datetime objects, Unix timestamps (int/float), ensuring the result
    is always timezone-aware (UTC).

    Args:
        expiry: Expiry value (datetime, int, or float timestamp)
        instrument_name: Optional instrument name for error messages

    Returns:
        Timezone-aware datetime object

    Raises:
        ValueError: If expiry type is unsupported or timestamp is invalid
    """
    if isinstance(expiry, datetime):
        if expiry.tzinfo is None:
            return expiry.replace(tzinfo=timezone.utc)
        return expiry

    if isinstance(expiry, (int, float)):
        try:
            return datetime.fromtimestamp(expiry, tz=timezone.utc)
        except (ValueError, OSError) as exc:
            context = f" for {instrument_name}" if instrument_name else ""
            raise ValueError(f"Invalid timestamp {expiry}{context}: {exc}") from exc

    context = f" for {instrument_name}" if instrument_name else ""
    raise ValueError(f"Expected datetime or numeric timestamp, got {type(expiry).__name__}{context}")


def is_market_expired(expiry: str) -> bool:
    """Determine whether a market has expired based on epoch time."""
    result = parse_iso_datetime(expiry)
    if result is None:
        return True
    _, time_point = result
    return time_point < (30 / (365.25 * 24 * 3600))
