from __future__ import annotations

"""Timezone and clock helper functions."""


import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Union

import pytz

from ..config_loader import get_reporting_timezone

logger = logging.getLogger(__name__)


def get_current_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def get_current_est() -> datetime:
    """Get current US/Eastern time as timezone-aware datetime."""
    est = pytz.timezone("US/Eastern")
    return datetime.now(est)


def get_current_date_in_timezone(timezone_name: str) -> datetime:
    """Get current datetime in the provided timezone name."""
    tz = pytz.timezone(timezone_name)
    return datetime.now(tz)


def get_timezone_aware_date(timezone_name: str = "America/New_York") -> date:
    """Return the current date in the requested timezone."""
    return get_current_date_in_timezone(timezone_name).date()


def load_configured_timezone() -> str:
    """Load timezone string from shared configuration, raising if unavailable."""
    return get_reporting_timezone()


def validate_timezone(tz_name: str) -> bool:
    """Return True when the timezone string is recognized by pytz."""
    try:
        pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        return False
    return True


def get_current_time(tz_name: str = "UTC") -> datetime:
    """Return current datetime in the requested timezone."""
    if not validate_timezone(tz_name):
        raise ValueError(f"Unknown timezone '{tz_name}'")
    tz = pytz.timezone(tz_name)
    return datetime.now(tz)


def ensure_timezone_aware(value: object) -> datetime:
    """
    Ensure datetime is timezone-aware, defaulting to UTC when naive.

    Args:
        value: Value (typically a string or datetime) to normalize

    Returns:
        Timezone-aware datetime

    Raises:
        TypeError: If value is not str or datetime
    """
    from dateutil import parser as dateutil_parser

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = dateutil_parser.isoparse(value)
    else:
        raise TypeError(f"Unsupported datetime value type: {type(value)!r}")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def to_utc(dt: datetime) -> datetime:
    """Convert a datetime to UTC, assuming naive values are already UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_start_of_day_utc(dt: Optional[datetime] = None) -> datetime:
    """Return the start of day in UTC for the provided datetime."""
    base = ensure_timezone_aware(dt or get_current_utc())
    return base.replace(hour=0, minute=0, second=0, microsecond=0)


def get_days_ago_utc(days: int) -> datetime:
    """Return the UTC datetime representing ``days`` days ago."""
    return get_current_utc() - timedelta(days=days)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string using ``datetime.strftime``."""
    return dt.strftime(format_str)


def format_timestamp(dt_input: Union[str, int, float, datetime], tz_name: str = "UTC") -> str:
    """Format a timestamp string that includes timezone abbreviation."""
    if not validate_timezone(tz_name):
        raise ValueError(f"Unknown timezone '{tz_name}'")

    if isinstance(dt_input, (int, float)):
        aware_dt = datetime.fromtimestamp(dt_input, tz=timezone.utc)
    else:
        aware_dt = ensure_timezone_aware(dt_input)

    tz = pytz.timezone(tz_name)
    localized = aware_dt.astimezone(tz)
    return localized.strftime("%Y-%m-%d %H:%M:%S %Z")


async def sleep_until_next_minute() -> None:
    """Suspend execution until the start of the next minute."""
    now = get_current_utc()
    next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    await asyncio.sleep((next_minute - now).total_seconds())
