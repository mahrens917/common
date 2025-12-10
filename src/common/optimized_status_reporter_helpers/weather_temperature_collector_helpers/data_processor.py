"""Weather data processing."""

from typing import Dict, List

from common.redis_protocol.converters import decode_redis_hash

DEFAULT_WEATHER_EMOJI = "🌡️"


def process_weather_results(
    station_codes: List[str], weather_results: List
) -> Dict[str, Dict[str, str]]:
    """
    Process weather data results into temperature dict.

    Args:
        station_codes: List of station codes
        weather_results: List of raw weather data from Redis

    Returns:
        Dict mapping station codes to temperature data
    """
    weather_temperatures: Dict[str, Dict[str, str]] = {}

    for station_code, weather_data_raw in zip(station_codes, weather_results):
        if not weather_data_raw:
            continue

        weather_data = decode_redis_hash(weather_data_raw)
        temp_f = weather_data.get("temp_f")
        if temp_f is None:
            continue

        emoticon_raw = weather_data.get("weather_emoticon")
        emoticon = emoticon_raw if isinstance(emoticon_raw, str) else DEFAULT_WEATHER_EMOJI

        weather_temperatures[station_code] = {
            "temp_f": str(temp_f),
            "emoticon": emoticon,
        }

    return weather_temperatures
