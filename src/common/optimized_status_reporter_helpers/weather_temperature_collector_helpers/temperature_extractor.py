"""Temperature data extraction from Redis weather data."""

from typing import Any, Dict, List

from common.redis_protocol.converters import decode_redis_hash

DEFAULT_WEATHER_EMOJI = "🌡️"


class TemperatureExtractor:
    """Extracts temperature data from weather station records."""

    @staticmethod
    async def extract_temperatures(redis_client, weather_keys: List[Any], station_codes: List[str]) -> Dict[str, Dict[str, str]]:
        """Extract temperature data from weather station keys."""
        if not weather_keys:
            return {}

        pipeline = redis_client.pipeline()
        for weather_key in weather_keys:
            pipeline.hgetall(weather_key)

        weather_results = await pipeline.execute()
        weather_temperatures: Dict[str, Dict[str, str]] = {}

        for station_code, weather_data_raw in zip(station_codes, weather_results):
            temp_data = TemperatureExtractor.process_weather_data(weather_data_raw)
            if temp_data:
                weather_temperatures[station_code] = temp_data

        return weather_temperatures

    @staticmethod
    def process_weather_data(weather_data_raw: Any) -> Dict[str, str]:
        """Process raw weather data and extract temperature info."""
        if not weather_data_raw:
            return {}

        weather_data = decode_redis_hash(weather_data_raw)
        temp_f = weather_data.get("temp_f")
        if temp_f is None:
            return {}

        emoticon_raw = weather_data.get("weather_emoticon")
        emoticon = emoticon_raw if isinstance(emoticon_raw, str) else DEFAULT_WEATHER_EMOJI

        return {"temp_f": str(temp_f), "emoticon": emoticon}
