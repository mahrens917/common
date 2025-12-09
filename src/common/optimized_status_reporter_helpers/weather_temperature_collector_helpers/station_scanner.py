"""Station scanning logic."""

from typing import Any, List, Tuple


async def scan_weather_stations(redis_client, station_prefix: str) -> Tuple[List[Any], List[str]]:
    """
    Scan Redis for weather station keys.

    Args:
        redis_client: Redis client instance
        station_prefix: Prefix for weather station keys

    Returns:
        Tuple of (weather_keys, station_codes)
    """
    weather_keys: List[Any] = []
    station_codes: List[str] = []

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
