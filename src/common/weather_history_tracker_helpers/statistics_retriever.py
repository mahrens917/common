"""Temperature history retrieval and statistics for weather stations"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import List, Tuple

from common.exceptions import ValidationError
from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.redis_schema import WeatherHistoryKey, ensure_uppercase_icao
from common.time_utils import get_current_utc

from .observation_recorder import _TEMP_MAX, _TEMP_MIN

logger = logging.getLogger(__name__)


class WeatherStatisticsRetriever:
    """Retrieves and processes weather station temperature history"""

    @staticmethod
    def _parse_entry(payload: bytes | str, score: float) -> Tuple[int, float] | None:
        """Parse temperature entry from Redis sorted set"""
        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            data = json.loads(payload)
            temp_f = float(data["temp_f"])
        except (  # policy_guard: allow-silent-handler
            ValueError,
            KeyError,
            json.JSONDecodeError,
            TypeError,
        ):
            return None
        else:
            if _TEMP_MIN <= temp_f <= _TEMP_MAX:
                return (int(score), temp_f)
            return None

    @staticmethod
    def _validate_station_input(station_icao: object) -> str:
        """Validate and normalize station ICAO code."""
        if not station_icao or not isinstance(station_icao, str):
            raise ValidationError(f"Invalid station_icao: {station_icao}")
        return ensure_uppercase_icao(station_icao)

    @staticmethod
    async def _fetch_redis_entries(client: RedisClient, station_icao: str, cutoff_ts: float) -> List[Tuple[bytes | str, float]]:
        """Fetch temperature entries within the time window from Redis for station."""
        redis_key = WeatherHistoryKey(icao=station_icao).key()
        entries = await ensure_awaitable(client.zrangebyscore(redis_key, cutoff_ts, "+inf", withscores=True))
        if not entries:
            logger.warning("No temperature history found for %s", station_icao)
            return []
        return entries

    @staticmethod
    def _filter_and_parse_entries(entries: List[Tuple[bytes | str, float]]) -> List[Tuple[int, float]]:
        """Filter entries by timestamp and parse temperature data."""
        invalid_count = 0
        temperature_history = []
        for payload, score in entries:
            parsed = WeatherStatisticsRetriever._parse_entry(payload, score)
            if parsed is None:
                invalid_count += 1
                continue
            temperature_history.append(parsed)
        temperature_history.sort(key=lambda x: x[0])
        if invalid_count > 0:
            logger.warning("%d invalid temperature entries (missing temp/out of range)", invalid_count)
        return temperature_history

    @staticmethod
    async def get_history(client: RedisClient, station_icao: str, hours: int = 24) -> List[Tuple[int, float]]:
        """
        Get temperature history for a weather station.

        Args:
            client: Redis client instance
            station_icao: Weather station ICAO code (e.g., 'KAUS', 'KMDW')
            hours: Number of hours of history to retrieve

        Returns:
            List of (timestamp, temp_f) tuples sorted by timestamp
        """
        station_icao = WeatherStatisticsRetriever._validate_station_input(station_icao)
        cutoff_ts = (get_current_utc() - timedelta(hours=hours)).timestamp()
        entries = await WeatherStatisticsRetriever._fetch_redis_entries(client, station_icao, cutoff_ts)

        if not entries:
            return []

        return WeatherStatisticsRetriever._filter_and_parse_entries(entries)
