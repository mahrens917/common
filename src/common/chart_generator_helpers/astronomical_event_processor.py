from __future__ import annotations

"""Helper for processing daily astronomical events"""


import logging
from datetime import datetime, timedelta, timezone, tzinfo
from typing import List, Tuple

from .config import AstronomicalEventData

logger = logging.getLogger("src.monitor.chart_generator")


class AstronomicalEventProcessor:
    """Processes astronomical events for a single day"""

    def process_day_astronomical_events(
        self,
        *,
        data: AstronomicalEventData,
    ) -> None:
        """Process astronomical events for a single day"""
        try:
            solar_noon = data.calculate_solar_noon_utc(data.latitude, data.longitude, data.current_date)
            if (data.start_date - timedelta(hours=12)) <= solar_noon <= (data.end_date + timedelta(hours=12)):
                data.vertical_lines.append((solar_noon, "orange", "Solar Noon"))

            local_midnight = data.calculate_local_midnight_utc(data.latitude, data.longitude, data.current_date)
            if (data.start_date - timedelta(hours=12)) <= local_midnight <= (data.end_date + timedelta(hours=12)):
                data.vertical_lines.append((local_midnight, "blue", "Local Midnight"))

            dawn = data.calculate_dawn_utc(data.latitude, data.longitude, data.current_date)
            if (data.start_date - timedelta(hours=12)) <= dawn <= (data.end_date + timedelta(hours=12)):
                data.vertical_lines.append((dawn, "lightsalmon", "Dawn"))

            dusk = data.calculate_dusk_utc(data.latitude, data.longitude, data.current_date)
            if (data.start_date - timedelta(hours=12)) <= dusk <= (data.end_date + timedelta(hours=12)):
                data.vertical_lines.append((dusk, "darkorange", "Dusk"))

            if dawn and dusk:
                self._add_dawn_dusk_period(dawn, dusk, data.local_tz, data.dawn_dusk_periods)
        except (  # policy_guard: allow-silent-handler
            RuntimeError,
            ValueError,
            TypeError,
        ) as exc:  # pragma: no cover - astro math failure
            logger.warning(
                "Failed to calculate solar times for %s: %s",
                data.current_date.date(),
                exc,
            )

    def _add_dawn_dusk_period(
        self,
        dawn: datetime,
        dusk: datetime,
        local_tz: tzinfo | None,
        dawn_dusk_periods: List[Tuple[datetime, datetime]],
    ) -> None:
        """Add dawn-to-dusk period with timezone conversion if needed"""
        if local_tz:
            dawn_local = dawn.replace(tzinfo=timezone.utc).astimezone(local_tz).replace(tzinfo=None)
            dusk_local = dusk.replace(tzinfo=timezone.utc).astimezone(local_tz).replace(tzinfo=None)
            dawn_dusk_periods.append((dawn_local, dusk_local))
            logger.debug("Added dawn/dusk period (local time): %s to %s", dawn_local, dusk_local)
        else:
            dawn_dusk_periods.append((dawn, dusk))
            logger.debug("Added dawn/dusk period (UTC): %s to %s", dawn, dusk)
