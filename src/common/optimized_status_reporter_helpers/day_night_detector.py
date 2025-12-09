"""
Day/night detection for weather stations.

Determines if a location is experiencing day or night based on coordinates.
"""

import json
import logging
import os
from typing import Dict

from src.common.time_utils import is_between_dawn_and_dusk

logger = logging.getLogger(__name__)


class DayNightDetector:
    """Detects day/night status for weather stations."""

    def __init__(self, moon_phase_calculator):
        self.moon_phase_calculator = moon_phase_calculator
        self._station_coordinates: Dict[str, Dict[str, float]] = {}

    def load_weather_station_coordinates(self) -> None:
        """Load weather station coordinates from configuration file."""
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config",
                "weather_station_mapping.json",
            )

            with open(config_path, "r") as f:
                config = json.load(f)

            # Extract coordinates by ICAO code
            coordinates = {}
            mappings = config.get("mappings")
            if isinstance(mappings, dict):
                for station_info in mappings.values():
                    if not isinstance(station_info, dict):
                        continue
                    icao = station_info.get("icao")
                    if (
                        isinstance(icao, str)
                        and "latitude" in station_info
                        and "longitude" in station_info
                    ):
                        coordinates[icao] = {
                            "latitude": station_info["latitude"],
                            "longitude": station_info["longitude"],
                        }

            self._station_coordinates = coordinates

        except (
            OSError,
            ValueError,
        ) as exc:
            logger.debug(
                "Weather station coordinates unavailable (%s): %s",
                type(exc).__name__,
            )
            self._station_coordinates = {}

    def get_day_night_icon(self, icao_code: str) -> str:
        """Get day/night icon based on station coordinates and current time."""
        try:
            if icao_code not in self._station_coordinates:
                return ""  # No coordinates available

            coords = self._station_coordinates[icao_code]
            latitude = coords["latitude"]
            longitude = coords["longitude"]

            # Check if it's currently between dawn and dusk at this location
            is_daytime = is_between_dawn_and_dusk(latitude, longitude)

            # Return empty string for daytime, moon phase emoji for nighttime
            if is_daytime:
                return ""
            return self.moon_phase_calculator.get_moon_phase_emoji()

        except (
            RuntimeError,
            ValueError,
            KeyError,
            TypeError,
        ):
            # Return empty string if day/night detection fails
            return ""
