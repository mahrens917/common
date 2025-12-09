"""Redis key scanning for weather stations."""

from typing import Any, List, Tuple


class KeyScanner:
    """Scans Redis for weather station keys."""

    @staticmethod
    async def scan_weather_keys(redis_client, station_prefix: str) -> Tuple[List[Any], List[str]]:
        """Scan Redis for weather station keys and extract station codes."""
        weather_keys: List[Any] = []
        station_codes: List[str] = []

        async for key in redis_client.scan_iter(match=f"{station_prefix}*", count=50):
            key_str = key.decode() if isinstance(key, bytes) else key
            if not KeyScanner.is_valid_weather_key(key_str, station_prefix):
                continue

            suffix = key_str[len(station_prefix) :]
            weather_keys.append(key)
            station_codes.append(suffix.upper())

        return weather_keys, station_codes

    @staticmethod
    def is_valid_weather_key(key_str: str, station_prefix: str) -> bool:
        """Check if key is a valid weather station key."""
        if not key_str.startswith(station_prefix):
            return False
        suffix = key_str[len(station_prefix) :]
        return bool(suffix) and ":" not in suffix
