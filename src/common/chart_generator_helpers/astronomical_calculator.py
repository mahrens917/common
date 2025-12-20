from __future__ import annotations

"""Helper for calculating astronomical features for weather charts"""


import logging
from datetime import datetime, timedelta, timezone, tzinfo
from typing import List, Optional, Tuple

from src.common.chart_generator.contexts import AstronomicalFeatures

from .astronomical_event_processor import AstronomicalEventProcessor
from .config import AstronomicalEventData

logger = logging.getLogger("src.monitor.chart_generator")


class AstronomicalCalculator:
    """Calculates dawn, dusk, and solar events for weather charts"""

    def __init__(self):
        self.event_processor = AstronomicalEventProcessor()

    def compute_astronomical_features(
        self,
        station_icao: str,
        station_coordinates: Optional[Tuple[float, float]],
        timestamps: List[datetime],
    ) -> AstronomicalFeatures:
        """Compute astronomical features for the chart time range"""
        if not station_coordinates:
            logger.warning(
                "No coordinates available for %s - skipping astronomical features", station_icao
            )
            return AstronomicalFeatures(vertical_lines=[], dawn_dusk_periods=None)

        latitude, longitude = station_coordinates
        logger.info("Calculating astronomical features for %s", station_icao)

        from common.time_utils import (
            calculate_dawn_utc,
            calculate_dusk_utc,
            calculate_local_midnight_utc,
            calculate_solar_noon_utc,
        )

        start_date = timestamps[0]
        end_date = timestamps[-1]

        try:
            local_tz = self._get_local_timezone(latitude, longitude, station_icao)

            current_date = (start_date - timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            if current_date.tzinfo is None:
                current_date = current_date.replace(tzinfo=timezone.utc)

            extended_end_date = end_date + timedelta(days=1)

            vertical_lines: List[Tuple[datetime, str, str]] = []
            dawn_dusk_periods: List[Tuple[datetime, datetime]] = []

            while current_date <= extended_end_date:
                event_data = AstronomicalEventData(
                    current_date=current_date,
                    latitude=latitude,
                    longitude=longitude,
                    start_date=start_date,
                    end_date=end_date,
                    local_tz=local_tz,
                    vertical_lines=vertical_lines,
                    dawn_dusk_periods=dawn_dusk_periods,
                    calculate_solar_noon_utc=calculate_solar_noon_utc,
                    calculate_local_midnight_utc=calculate_local_midnight_utc,
                    calculate_dawn_utc=calculate_dawn_utc,
                    calculate_dusk_utc=calculate_dusk_utc,
                )
                self.event_processor.process_day_astronomical_events(data=event_data)
                current_date += timedelta(days=1)

            logger.info(
                "Added %s astronomical lines and %s shading periods",
                len(vertical_lines),
                len(dawn_dusk_periods),
            )
            return AstronomicalFeatures(
                vertical_lines=vertical_lines,
                dawn_dusk_periods=dawn_dusk_periods or None,
            )
        except (
            RuntimeError,
            ValueError,
            TypeError,
        ) as exc:  # pragma: no cover - error recovery path
            logger.warning(
                "Failed to compute astronomical features for %s: %s",
                station_icao,
                exc,
                exc_info=True,
            )
            return AstronomicalFeatures(vertical_lines=[], dawn_dusk_periods=None)

    def _get_local_timezone(
        self, latitude: float, longitude: float, station_icao: str
    ) -> Optional[tzinfo]:
        """Get local timezone for coordinates"""
        try:
            import pytz

            from common.time_utils import get_timezone_from_coordinates

            timezone_name = get_timezone_from_coordinates(latitude, longitude)
            local_tz = pytz.timezone(timezone_name)
            logger.debug("Using local timezone %s for %s", timezone_name, station_icao)
        except (
            RuntimeError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:  # pragma: no cover - geo lookup failure
            logger.warning("Failed to get timezone for %s: %s", station_icao, exc)
            return None
        else:
            return local_tz
