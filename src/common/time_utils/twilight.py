from __future__ import annotations

"""Dawn/dusk calculations for Kalshi weather utilities."""

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from .base import AstronomicalComputationError, logger
from .solar import calculate_solar_noon_utc

# Constants
_CONST_180 = 180
_CONST_24 = 24
_CONST_90 = 90
_CONST_NEG_180 = -180
_CONST_NEG_90 = -90


def calculate_dawn_utc(latitude: float, longitude: float, date) -> datetime:
    """Calculate dawn (civil twilight) in UTC for a given location/date."""
    return _calculate_twilight(latitude, longitude, date, is_dawn=True)


def calculate_dusk_utc(latitude: float, longitude: float, date) -> datetime:
    """Calculate dusk (civil twilight) in UTC for a given location/date."""
    return _calculate_twilight(latitude, longitude, date, is_dawn=False)


def _calculate_twilight(latitude: float, longitude: float, date, *, is_dawn: bool) -> datetime:
    _validate_coordinates(latitude, longitude)
    date_utc = _normalize_date(date)
    day_of_year = date_utc.timetuple().tm_yday
    declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
    hour_angle = _compute_hour_angle(latitude, declination, date_utc, longitude, is_dawn)
    minutes = _compute_minutes_offset(hour_angle, longitude, day_of_year, is_dawn)
    result = _build_twilight_datetime(date_utc, minutes)
    _log_twilight(latitude, longitude, date_utc, result, is_dawn)
    return result


def _validate_coordinates(latitude: float, longitude: float) -> None:
    if not (_CONST_NEG_90 <= latitude <= _CONST_90):
        raise ValueError(f"Latitude {latitude} is out of valid range [-90, 90]")
    if not (_CONST_NEG_180 <= longitude <= _CONST_180):
        raise ValueError(f"Longitude {longitude} is out of valid range [-180, 180]")


def _normalize_date(date) -> datetime:
    if isinstance(date, datetime):
        if date.tzinfo is not None:
            return date.astimezone(timezone.utc)
        return datetime.combine(date.date(), datetime.min.time(), timezone.utc)
    return datetime.combine(date, datetime.min.time(), timezone.utc)


def _compute_hour_angle(latitude: float, declination: float, date_utc: datetime, longitude: float, is_dawn: bool) -> float:
    lat_rad = math.radians(latitude)
    decl_rad = math.radians(declination)
    twilight_rad = math.radians(-6.0)
    try:
        cos_hour_angle = (math.sin(twilight_rad) - math.sin(lat_rad) * math.sin(decl_rad)) / (math.cos(lat_rad) * math.cos(decl_rad))
        if not -1 <= cos_hour_angle <= 1:
            # Generate appropriate message based on event type (dawn/dusk)
            event_name = "dawn" if is_dawn else "dusk"
            message = f"Polar day prevents {event_name} calculation for lat={latitude}, lon={longitude}, date={date_utc.date()}"
            raise AstronomicalComputationError(message)
        return math.degrees(math.acos(cos_hour_angle))
    except (ValueError, ZeroDivisionError) as exc:  # policy_guard: allow-silent-handler
        logger.exception(
            "Twilight calculation failed for lat=%s, lon=%s, date=%s",
            latitude,
            longitude,
            date_utc.date(),
        )
        raise ValueError("Unable to compute twilight for provided coordinates") from exc


def _compute_minutes_offset(hour_angle: float, longitude: float, day_of_year: int, is_dawn: bool) -> float:
    B = 2 * math.pi * (day_of_year - 81) / 365
    equation_of_time = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
    longitude_correction = -4 * longitude
    minutes = 12 * 60 + (hour_angle * 4 if not is_dawn else -hour_angle * 4)
    return minutes + longitude_correction + equation_of_time


def _build_twilight_datetime(date_utc: datetime, minutes: float) -> datetime:
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    seconds = int((minutes % 1) * 60)
    twilight_date = date_utc.date()
    if hours >= _CONST_24:
        hours -= 24
        twilight_date += timedelta(days=1)
    elif hours < 0:
        hours += 24
        twilight_date -= timedelta(days=1)
    return datetime.combine(
        twilight_date,
        datetime.min.time().replace(hour=hours, minute=mins, second=seconds),
        timezone.utc,
    )


def _log_twilight(latitude: float, longitude: float, date_utc: datetime, result: datetime, is_dawn: bool) -> None:
    label = "dawn" if is_dawn else "dusk"
    logger.debug(
        "%s calculation: lat=%s, lon=%s, date=%s, %s=%s",
        label.capitalize(),
        latitude,
        longitude,
        date_utc.date(),
        label,
        result.isoformat(),
    )


def is_between_dawn_and_dusk(latitude: float, longitude: float, current_time: Optional[datetime] = None) -> bool:
    """Return True when current time sits between dawn and dusk."""
    current_time = current_time or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    dawn_current = calculate_dawn_utc(latitude, longitude, current_time)
    dusk_current = calculate_dusk_utc(latitude, longitude, current_time)

    previous_day = current_time - timedelta(days=1)
    dawn_previous = calculate_dawn_utc(latitude, longitude, previous_day)
    dusk_previous = calculate_dusk_utc(latitude, longitude, previous_day)

    next_day = current_time + timedelta(days=1)
    dawn_next = calculate_dawn_utc(latitude, longitude, next_day)
    dusk_next = calculate_dusk_utc(latitude, longitude, next_day)

    is_daylight = any(
        start <= current_time <= end
        for start, end in (
            (dawn_current, dusk_current),
            (dawn_previous, dusk_previous),
            (dawn_next, dusk_next),
        )
    )

    logger.debug(
        "Daylight window: current=%s, dawn_current=%s, dusk_current=%s, is_daylight=%s",
        current_time.isoformat(),
        dawn_current.isoformat(),
        dusk_current.isoformat(),
        is_daylight,
    )
    return is_daylight


def is_after_midpoint_noon_to_dusk(latitude: float, longitude: float, current_time: Optional[datetime] = None) -> bool:
    """Check if ``current_time`` is after the midpoint between solar noon and dusk."""
    current_time = current_time or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    solar_noon = calculate_solar_noon_utc(latitude, longitude, current_time)
    dusk = calculate_dusk_utc(latitude, longitude, current_time)
    midpoint = solar_noon + (dusk - solar_noon) / 2

    logger.debug(
        "Midpoint check: current=%s, solar_noon=%s, dusk=%s, midpoint=%s, after_midpoint=%s",
        current_time.isoformat(),
        solar_noon.isoformat(),
        dusk.isoformat(),
        midpoint.isoformat(),
        current_time >= midpoint,
    )
    return current_time >= midpoint


__all__ = [
    "calculate_dawn_utc",
    "calculate_dusk_utc",
    "is_after_midpoint_noon_to_dusk",
    "is_between_dawn_and_dusk",
]
