from __future__ import annotations

import zoneinfo
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from typing import List, Optional, Sequence, Tuple

from common.time_utils import get_timezone_from_coordinates


@dataclass(frozen=True)
class LocalizedTimestamps:
    """Localized representation of UTC timestamps for plotting."""

    timestamps: List[datetime]
    timezone: tzinfo


def ensure_naive_timestamps(timestamps: Sequence[datetime]) -> List[datetime]:
    """Return a copy of timestamps with timezone information stripped."""
    return [ts.replace(tzinfo=None) if ts.tzinfo is not None else ts for ts in timestamps]


def build_axis_timestamps(
    timestamps: Sequence[datetime],
    prediction_timestamps: Optional[Sequence[datetime]],
) -> List[datetime]:
    """Compose a sorted list of timestamps used for axis configuration."""
    combined = list(timestamps)
    if prediction_timestamps:
        combined.extend(prediction_timestamps)
        combined.sort()
    return combined


def localize_temperature_timestamps(
    timestamps_naive: Sequence[datetime],
    station_coordinates: Tuple[float, float],
) -> LocalizedTimestamps:
    """
    Convert UTC-naive timestamps to the station's local timezone.

    Args:
        timestamps_naive: Iterable of UTC timestamps without tzinfo.
        station_coordinates: Latitude and longitude of the station.

    Returns:
        LocalizedTimestamps with naive datetimes suitable for matplotlib.
    """
    latitude, longitude = station_coordinates
    timezone_name = get_timezone_from_coordinates(latitude, longitude)
    local_tz = zoneinfo.ZoneInfo(timezone_name)

    localized: List[datetime] = []
    for ts in timestamps_naive:
        ts_utc = ts.replace(tzinfo=timezone.utc)
        ts_local = ts_utc.astimezone(local_tz)
        localized.append(ts_local.replace(tzinfo=None))

    return LocalizedTimestamps(localized, local_tz)
