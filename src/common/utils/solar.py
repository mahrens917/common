"""Solar position calculations for diurnal cycle features.

Computes sunrise, sunset, and solar noon times based on station location and date.
Uses NOAA solar calculation formulas.

Canonical source — originally in zeus/src/common/solar_utils.py, extracted here
so that zeus, weather, and any future consumer share identical math (critical for
ML model consistency).
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, time
from typing import NamedTuple, Optional


class SolarTimes(NamedTuple):
    """Sunrise, solar noon, and sunset times for a location and date."""

    sunrise: time
    solar_noon: time
    sunset: time


# ---------------------------------------------------------------------------
# Internal helpers (NOAA formulas)
# ---------------------------------------------------------------------------

# Axial tilt used in the original zeus model training.  Do NOT replace with
# common.time_utils.base.EARTH_AXIAL_TILT_DEG (23.4393) — the value 23.45 was
# baked into trained model weights and changing it would introduce prediction
# drift.
_AXIAL_TILT_DEG = 23.45


def _julian_day(d: date) -> float:
    """Calculate Julian day number from a date."""
    a = (14 - d.month) // 12
    y = d.year + 4800 - a
    m = d.month + 12 * a - 3
    return d.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def _solar_declination(day_of_year: int) -> float:
    """Calculate solar declination angle in radians."""
    return math.radians(-_AXIAL_TILT_DEG) * math.cos(2 * math.pi * (day_of_year + 10) / 365)


def _equation_of_time(day_of_year: int) -> float:
    """Calculate equation of time correction in minutes."""
    b = 2 * math.pi * (day_of_year - 81) / 365
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def _hour_angle_sunrise(lat_rad: float, declination: float) -> float:
    """Calculate hour angle at sunrise in radians.

    Returns NaN for polar day/night conditions.
    """
    cos_ha = -math.tan(lat_rad) * math.tan(declination)
    if cos_ha < -1:
        return math.pi  # Polar day - sun never sets
    if cos_ha > 1:
        return 0.0  # Polar night - sun never rises
    return math.acos(cos_ha)


# ---------------------------------------------------------------------------
# Public API — solar times
# ---------------------------------------------------------------------------


def compute_solar_times(latitude: float, longitude: float, d: date) -> SolarTimes:
    """Compute sunrise, solar noon, and sunset for a location and date.

    Args:
        latitude: Station latitude in degrees (-90 to 90)
        longitude: Station longitude in degrees (-180 to 180)
        d: Date for calculation

    Returns:
        SolarTimes with sunrise, solar_noon, sunset as time objects (UTC)
    """
    day_of_year = d.timetuple().tm_yday
    lat_rad = math.radians(latitude)

    declination = _solar_declination(day_of_year)
    eot = _equation_of_time(day_of_year)
    hour_angle = _hour_angle_sunrise(lat_rad, declination)

    # Solar noon in UTC (hours from midnight)
    # Longitude correction: 4 minutes per degree west of prime meridian
    solar_noon_utc = 12.0 - (longitude / 15.0) - (eot / 60.0)

    # Sunrise and sunset
    day_length_hours = 2 * math.degrees(hour_angle) / 15.0
    sunrise_utc = solar_noon_utc - day_length_hours / 2
    sunset_utc = solar_noon_utc + day_length_hours / 2

    def hours_to_time(h: float) -> time:
        """Convert fractional hours to time object, wrapping at 24."""
        h = h % 24  # Wrap around midnight
        hours = int(h)
        minutes = int((h - hours) * 60)
        seconds = int(((h - hours) * 60 - minutes) * 60)
        return time(hours, minutes, seconds)

    return SolarTimes(
        sunrise=hours_to_time(sunrise_utc),
        solar_noon=hours_to_time(solar_noon_utc),
        sunset=hours_to_time(sunset_utc),
    )


# ---------------------------------------------------------------------------
# Public API — diurnal fraction
# ---------------------------------------------------------------------------


def compute_solar_diurnal(
    obs_time: datetime,
    latitude: float,
    longitude: float,
) -> float:
    """Compute solar diurnal fraction for an observation.

    Args:
        obs_time: Observation datetime (should be in local time or UTC consistently)
        latitude: Station latitude in degrees
        longitude: Station longitude in degrees

    Returns:
        Diurnal fraction:
        - 0.0 at sunrise
        - 0.5 at solar noon
        - 1.0 at sunset
        - <0 before sunrise
        - >1 after sunset
    """
    d = obs_time.date()
    solar = compute_solar_times(latitude, longitude, d)

    # Convert times to fractional hours for comparison
    def time_to_hours(t: time) -> float:
        return t.hour + t.minute / 60 + t.second / 3600

    obs_hours = time_to_hours(obs_time.time())
    sunrise_hours = time_to_hours(solar.sunrise)
    sunset_hours = time_to_hours(solar.sunset)

    # Handle day crossing (rare, but possible near poles)
    if sunset_hours < sunrise_hours:
        sunset_hours += 24
        if obs_hours < sunrise_hours:
            obs_hours += 24

    day_length = sunset_hours - sunrise_hours
    if day_length <= 0:
        # Polar night - return 0.5 (midpoint)
        return 0.5

    diurnal = (obs_hours - sunrise_hours) / day_length
    return diurnal


# ---------------------------------------------------------------------------
# Public API — day-of-year encoding
# ---------------------------------------------------------------------------


def compute_day_of_year_encoding(obs_time: datetime) -> tuple[float, float]:
    """Compute sin/cos encoding of day of year for cyclical seasonal representation.

    Uses sin/cos encoding to ensure:
    - Dec 31 -> Jan 1 transition is smooth (adjacent on unit circle)
    - Every day maps to a unique (sin, cos) point
    - Days close in time are close in feature space

    Args:
        obs_time: Observation datetime

    Returns:
        Tuple of (sin, cos) where angle = 2pi x (day-1) / 365.25
        Using 365.25 to account for leap years on average.
    """
    day_of_year = obs_time.timetuple().tm_yday
    angle = 2 * math.pi * (day_of_year - 1) / 365.25
    return float(math.sin(angle)), float(math.cos(angle))


# ---------------------------------------------------------------------------
# Public API — ISO convenience wrapper (used by weather)
# ---------------------------------------------------------------------------

# Regex pattern for valid ISO 8601 timestamps
_ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$")


def _is_valid_iso_timestamp(value: str) -> bool:
    """Check if value is a valid ISO timestamp string."""
    if not value or not isinstance(value, str):
        return False
    return bool(_ISO_PATTERN.match(value))


def compute_solar_diurnal_from_iso(
    obs_time_iso: str,
    latitude: float,
    longitude: float,
) -> Optional[float]:
    """Compute solar diurnal from ISO timestamp string.

    Args:
        obs_time_iso: ISO format timestamp (e.g., "2024-01-15T14:30:00Z")
        latitude: Station latitude
        longitude: Station longitude

    Returns:
        Diurnal fraction, or None if parsing fails
    """
    if not _is_valid_iso_timestamp(obs_time_iso):
        return None
    obs_time = datetime.fromisoformat(obs_time_iso.replace("Z", "+00:00"))
    return compute_solar_diurnal(obs_time, latitude, longitude)


__all__ = [
    "SolarTimes",
    "compute_solar_times",
    "compute_solar_diurnal",
    "compute_solar_diurnal_from_iso",
    "compute_day_of_year_encoding",
]
