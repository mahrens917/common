from __future__ import annotations

"""Solar noon calculations and helpers."""

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from .base import logger

# Constants
_CONST_180 = 180
_CONST_24 = 24
_CONST_90 = 90
_CONST_NEG_180 = -180
_CONST_NEG_90 = -90


def calculate_solar_noon_utc(latitude: float, longitude: float, date) -> datetime:
    """
    Calculate solar noon time in UTC for a given location and date.

    Solar noon is when the sun reaches its highest point in the sky at a given location.
    This calculation uses the equation of time and longitude offset to determine
    the precise solar noon time.
    """
    if not (_CONST_NEG_90 <= latitude <= _CONST_90):
        raise ValueError(f"Latitude {latitude} is out of valid range [-90, 90]")
    if not (_CONST_NEG_180 <= longitude <= _CONST_180):
        raise ValueError(f"Longitude {longitude} is out of valid range [-180, 180]")

    if isinstance(date, datetime):
        if date.tzinfo is not None:
            date_utc = date.astimezone(timezone.utc)
        else:
            date_utc = date.replace(tzinfo=timezone.utc)
    else:
        date_utc = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)

    day_of_year = date_utc.timetuple().tm_yday

    B = 2 * math.pi * (day_of_year - 81) / 365
    equation_of_time = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)

    longitude_correction = -4 * longitude
    solar_noon_minutes = 12 * 60 + longitude_correction + equation_of_time

    solar_noon_hours = int(solar_noon_minutes // 60)
    solar_noon_mins = int(solar_noon_minutes % 60)
    solar_noon_seconds = int((solar_noon_minutes % 1) * 60)

    solar_noon_date = date_utc.date()
    if solar_noon_hours >= _CONST_24:
        solar_noon_hours -= 24
        solar_noon_date = solar_noon_date + timedelta(days=1)
    elif solar_noon_hours < 0:
        solar_noon_hours += 24
        solar_noon_date = solar_noon_date - timedelta(days=1)

    solar_noon_utc = datetime.combine(
        solar_noon_date,
        datetime.min.time().replace(hour=solar_noon_hours, minute=solar_noon_mins, second=solar_noon_seconds),
        timezone.utc,
    )

    logger.debug(
        "Solar noon calculation: lat=%s, lon=%s, date=%s, solar_noon=%s",
        latitude,
        longitude,
        date_utc.date(),
        solar_noon_utc.isoformat(),
    )

    return solar_noon_utc


def is_after_solar_noon(latitude: float, longitude: float, current_time: Optional[datetime] = None) -> bool:
    """Check if the current time is after solar noon for a given location."""
    current_time = current_time or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    solar_noon_current = calculate_solar_noon_utc(latitude, longitude, current_time)
    previous_day = current_time - timedelta(days=1)
    solar_noon_previous = calculate_solar_noon_utc(latitude, longitude, previous_day)

    diff_current = abs((current_time - solar_noon_current).total_seconds())
    diff_previous = abs((current_time - solar_noon_previous).total_seconds())

    if diff_current <= diff_previous:
        relevant_solar_noon = solar_noon_current
        is_after = current_time >= solar_noon_current
    else:
        relevant_solar_noon = solar_noon_previous
        is_after = current_time >= solar_noon_previous

    logger.debug(
        "Solar noon check: current=%s, solar_noon_current=%s, solar_noon_previous=%s, " "selected_solar_noon=%s, is_after=%s",
        current_time.isoformat(),
        solar_noon_current.isoformat(),
        solar_noon_previous.isoformat(),
        relevant_solar_noon.isoformat(),
        is_after,
    )

    return is_after


__all__ = ["calculate_solar_noon_utc", "is_after_solar_noon"]
