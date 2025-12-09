"""
Weather section generation for status report.

Formats weather station data with day/night indicators.
"""

from typing import Any, Dict, List

DEFAULT_WEATHER_EMOJI = "🌡️"


class WeatherSectionGenerator:
    """Generates formatted weather section lines."""

    def __init__(self, day_night_detector, data_coercion):
        self.day_night_detector = day_night_detector
        self.data_coercion = data_coercion

    def generate_weather_section(self, weather_temperatures: Dict[str, Any]) -> List[str]:
        """Generate weather section lines with day/night indicators."""
        if not weather_temperatures:
            return []

        lines = ["🌡️ Weather:"]

        # Sort by longitude (east to west) using loaded coordinates
        def sort_key(icao: str) -> float:
            coords = self.day_night_detector._station_coordinates.get(icao)
            if coords and "longitude" in coords:
                return coords["longitude"]
            # Default to far west if coordinates missing so we list known stations first
            return -9999.0

        for icao_code in sorted(weather_temperatures.keys(), key=sort_key, reverse=True):
            weather_info_raw = weather_temperatures[icao_code]
            if not isinstance(weather_info_raw, dict):
                continue
            temp_raw = weather_info_raw.get("temp_f")
            if temp_raw is None or not isinstance(temp_raw, (int, float, str)):
                continue
            try:
                temp_value = float(temp_raw)
            except (
                TypeError,
                ValueError,
            ):
                continue
            emoticon = self.data_coercion.string_or_default(
                weather_info_raw.get("emoticon"),
                DEFAULT_WEATHER_EMOJI,
            )

            # Add day/night indicator
            day_night_icon = self.day_night_detector.get_day_night_icon(icao_code)

            lines.append(f"  {emoticon} {icao_code}: {temp_value:.0f}°F {day_night_icon}")

        return lines
