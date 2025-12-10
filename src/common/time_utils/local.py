from __future__ import annotations

"""Local timezone calculations for weather stations."""

import zoneinfo
from datetime import datetime, timezone
from typing import Optional

from ..time_helpers.location import get_timezone_from_coordinates
from .base import logger

# Constants
_CONST_180 = 180
_CONST_90 = 90
_CONST_NEG_180 = -180
_CONST_NEG_90 = -90


def calculate_local_midnight_utc(latitude: float, longitude: float, date: datetime) -> datetime:
    """
    Calculate local midnight in UTC for a given location and date.
    """
    if not (_CONST_NEG_90 <= latitude <= _CONST_90):
        raise ValueError(f"Latitude {latitude} is out of valid range [-90, 90]")
    if not (_CONST_NEG_180 <= longitude <= _CONST_180):
        raise ValueError(f"Longitude {longitude} is out of valid range [-180, 180]")

    date_utc = date.astimezone(timezone.utc) if date.tzinfo else date.replace(tzinfo=timezone.utc)
    timezone_name = get_timezone_from_coordinates(latitude, longitude)

    try:
        local_tz = zoneinfo.ZoneInfo(timezone_name)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError) as exc:
        logger.exception(
            "Failed to load timezone %s for coordinates lat=%s, lon=%s: %s",
            timezone_name,
            latitude,
            longitude,
            exc,
        )
        raise ValueError(
            (
                "Cannot determine timezone for coordinates lat={lat}, lon={lon}. "
                "Timezone lookup returned '{tz}' but failed to load: {error}"
            ).format(lat=latitude, lon=longitude, tz=timezone_name, error=exc)
        ) from exc

    date_local = date_utc.astimezone(local_tz)
    local_midnight = datetime.combine(date_local.date(), datetime.min.time(), local_tz)
    local_midnight_utc = local_midnight.astimezone(timezone.utc)

    logger.debug(
        "Local midnight calculation: lat=%s, lon=%s, date=%s, timezone=%s, local_midnight=%s",
        latitude,
        longitude,
        date_utc.date(),
        timezone_name,
        local_midnight_utc.isoformat(),
    )
    return local_midnight_utc


def is_after_local_midnight(
    latitude: float, longitude: float, current_time: Optional[datetime] = None
) -> bool:
    """Check whether ``current_time`` falls after local midnight."""
    current_time = current_time or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    # Use late binding to get calculate_local_midnight_utc from time_utils to allow monkeypatching
    # Import at runtime to avoid circular imports
    import sys

    time_utils_module = sys.modules.get("common.time_utils")
    if time_utils_module and hasattr(time_utils_module, "calculate_local_midnight_utc"):
        _calc_midnight = getattr(time_utils_module, "calculate_local_midnight_utc")
    else:
        _calc_midnight = calculate_local_midnight_utc

    local_midnight = _calc_midnight(latitude, longitude, current_time)
    is_after = current_time >= local_midnight

    logger.debug(
        "Local midnight check: current=%s, local_midnight=%s, is_after=%s",
        current_time.isoformat(),
        local_midnight.isoformat(),
        is_after,
    )
    return is_after


__all__ = [
    "calculate_local_midnight_utc",
    "is_after_local_midnight",
]
