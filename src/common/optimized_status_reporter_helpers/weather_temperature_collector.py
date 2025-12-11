"""
Weather temperature data collection from Redis.

Gathers current temperatures for all weather stations.
"""

from typing import Any, Dict, List

from common.redis_protocol.converters import decode_redis_hash
from common.redis_schema import WeatherStationKey

DEFAULT_WEATHER_EMOJI = "🌡️"


class WeatherTemperatureCollector:
    """Collects weather station temperature data."""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

    async def collect_weather_temperatures(self) -> Dict[str, Dict[str, str]]:
        """Collect temperature data for all weather stations."""
        weather_keys, station_codes = await _discover_weather_keys(self.redis_client)
        if not weather_keys:
            return {}

        weather_results = await _fetch_weather_hashes(self.redis_client, weather_keys)
        return _build_temperature_map(station_codes, weather_results)


async def _discover_weather_keys(redis_client) -> tuple[List[Any], List[str]]:
    """Scan Redis for weather station hashes."""
    weather_keys: List[Any] = []
    station_codes: List[str] = []
    station_prefix = WeatherStationKey(icao="TEST").key().rsplit(":", 1)[0] + ":"

    async for key in redis_client.scan_iter(match=f"{station_prefix}*", count=50):
        key_str = key.decode() if isinstance(key, bytes) else key
        if not key_str.startswith(station_prefix):
            continue
        suffix = key_str[len(station_prefix) :]
        if not suffix or ":" in suffix:
            continue

        weather_keys.append(key)
        station_codes.append(suffix.upper())

    return weather_keys, station_codes


async def _fetch_weather_hashes(redis_client, weather_keys: List[Any]) -> List[Dict[str, Any]]:
    """Fetch all weather hashes using a pipeline."""
    pipeline = redis_client.pipeline()
    for weather_key in weather_keys:
        pipeline.hgetall(weather_key)
    return await pipeline.execute()


def _build_temperature_map(station_codes: List[str], weather_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Convert Redis hash payloads into a mapping of station temps."""
    weather_temperatures: Dict[str, Dict[str, str]] = {}
    for station_code, weather_data_raw in zip(station_codes, weather_results):
        record = _parse_station_weather(weather_data_raw)
        if record:
            weather_temperatures[station_code] = record
    return weather_temperatures


def _parse_station_weather(weather_data_raw: Dict[str, Any]) -> Dict[str, str] | None:
    """Parse a single weather hash result into temperature/emoticon data."""
    if not weather_data_raw:
        return None
    weather_data = decode_redis_hash(weather_data_raw)
    temp_f = weather_data.get("temp_f")
    if temp_f is None:
        return None
    emoticon_raw = weather_data.get("weather_emoticon")
    emoticon = emoticon_raw if isinstance(emoticon_raw, str) else DEFAULT_WEATHER_EMOJI
    return {"temp_f": str(temp_f), "emoticon": emoticon}
