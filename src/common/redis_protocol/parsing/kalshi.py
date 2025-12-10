from __future__ import annotations

"""Ticker and expiry parsing helpers for Kalshi markets."""


from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from common.exceptions import DataError, ValidationError

# Constants
_CONST_2 = 2
_CONST_4 = 4
_CONST_5 = 5


def parse_expiry_token(token: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """Convert Kalshi expiry tokens to UTC datetimes."""
    normalized = _normalize_token(token)
    if not normalized:
        return None

    month = _parse_month_code(normalized)
    if month is None:
        return None
    prefix = normalized[:2]
    remainder = normalized[_CONST_5:]

    if not prefix.isdigit():
        return None

    if _is_year_month_day_format(remainder):
        return parse_year_month_day_format(normalized, prefix, month, remainder)

    day = _parse_day_from_prefix(normalized, prefix)
    return _parse_expiry_by_remainder(normalized, remainder, month, day, now)


def _normalize_token(token: str) -> Optional[str]:
    """Trim and uppercase tokens with minimal validation."""
    if not token or len(token.strip()) < _CONST_5:
        return None
    return token.strip().upper()


def _is_year_month_day_format(remainder: str) -> bool:
    """Return True when remainder is a 2-digit day segment."""
    return len(remainder) == _CONST_2 and remainder.isdigit()


def _parse_expiry_by_remainder(
    token: str, remainder: str, month: int, day: int, now: Optional[datetime]
) -> Optional[datetime]:
    """Handle the remainder segment to produce a datetime."""
    reference_time = now or datetime.now(timezone.utc)

    if len(remainder) == _CONST_4 and remainder.isdigit():
        return parse_intraday_format(token, reference_time, month, day, remainder)

    if len(remainder) == _CONST_2 and remainder.isdigit():
        return parse_day_month_year_format(token, month, day, remainder)

    if remainder:
        raise DataError(f"Unrecognized expiry token format '{token}'")
    raise ValueError(f"Expiry token '{token}' missing time or year segment")


def _parse_month_code(token: str) -> Optional[int]:
    """Parse month code from token and return month number"""
    month_map = {
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
    month_code = token[_CONST_2:5]
    return month_map.get(month_code)


def _parse_day_from_prefix(token: str, prefix: str) -> int:
    """Parse day value from token prefix"""
    try:
        return int(prefix)
    except ValueError as exc:
        raise ValidationError(f"Invalid day segment in expiry token '{token}'") from exc


def parse_year_month_day_format(token: str, prefix: str, month: int, remainder: str) -> datetime:
    """Parse YYMMMDD format (e.g., 25JAN01)"""
    try:
        year = 2000 + int(prefix)
        day = int(remainder)
    except ValueError as exc:
        raise ValidationError(f"Invalid year/day segment in expiry token '{token}'") from exc

    try:
        local_dt = datetime(year, month, day, 23, 59, tzinfo=ZoneInfo("America/New_York"))
    except ValueError as exc:
        raise ValidationError(f"Invalid calendar date in expiry token '{token}'") from exc

    return local_dt.astimezone(timezone.utc)


def parse_intraday_format(
    token: str, now: datetime, month: int, day: int, remainder: str
) -> datetime:
    """Parse DDMMMHHMM format (e.g., 01JAN1530)"""
    hour = int(remainder[:2])
    minute = int(remainder[_CONST_2:])
    try:
        candidate = datetime(now.year, month, day, hour, minute, tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValidationError(f"Invalid timestamp segment in expiry token '{token}'") from exc

    if candidate < now - timedelta(hours=1):
        candidate = datetime(now.year + 1, month, day, hour, minute, tzinfo=timezone.utc)
    return candidate


def parse_day_month_year_format(token: str, month: int, day: int, remainder: str) -> datetime:
    """Parse DDMMMYY format (e.g., 01JAN25)"""
    year = 2000 + int(remainder)
    try:
        return datetime(year, month, day, 8, 0, tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValidationError(f"Invalid calendar date in expiry token '{token}'") from exc


def derive_strike_fields(
    market_ticker: str,
) -> Optional[Tuple[str, Optional[float], Optional[float], float]]:
    """Extract strike metadata from a Kalshi ticker."""

    parts = market_ticker.upper().split("-")
    if not parts:
        return None

    strike_segment = parts[-1]
    if not strike_segment:
        return None

    prefix = strike_segment[0]
    value_str = strike_segment[1:] if prefix.isalpha() else strike_segment

    try:
        strike_value = float(value_str)
    except ValueError:
        return None

    strike_type = "greater"
    floor_strike: Optional[float] = strike_value
    cap_strike: Optional[float] = None

    if prefix.upper() == "B":
        strike_type = "less"
        floor_strike = None
        cap_strike = strike_value
    elif prefix.upper() == "T":
        strike_type = "greater"
        floor_strike = strike_value
        cap_strike = None
    elif prefix.upper() == "M":
        strike_type = "between"
        floor_strike = None
        cap_strike = None

    return strike_type, floor_strike, cap_strike, strike_value
