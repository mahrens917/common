"""Temperature history retrieval and statistics for weather stations"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import List, Tuple

from redis.exceptions import RedisError

from common.exceptions import ValidationError
from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.redis_schema import WeatherHistoryKey, ensure_uppercase_icao
from common.redis_utils import RedisOperationError
from common.time_utils import get_current_utc

logger = logging.getLogger(__name__)

REDIS_ERRORS = (
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)


# Constants
_TEMP_MAX = 200
_TEMP_MIN = -200


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
            if _TEMP_MIN <= temp_f <= _TEMP_MAX:
                return (int(score), temp_f)
        except (  # policy_guard: allow-silent-handler
            ValueError,
            KeyError,
            json.JSONDecodeError,
            TypeError,
        ):
            return None
        else:
            return None

    @staticmethod
    def _validate_station_input(station_icao: object) -> str:
        """Validate and normalize station ICAO code."""
        if not station_icao or not isinstance(station_icao, str):
            raise ValidationError(f"Invalid station_icao: {station_icao}")
        return ensure_uppercase_icao(station_icao)

    @staticmethod
    async def _fetch_redis_entries(client: RedisClient, station_icao: str) -> List[Tuple[bytes | str, float]]:
        """Fetch all temperature entries from Redis for station."""
        redis_key = WeatherHistoryKey(icao=station_icao).key()
        entries = await ensure_awaitable(client.zrange(redis_key, 0, -1, withscores=True))
        if not entries:
            logger.warning(f"No temperature history found for {station_icao}")
            return []
        return entries

    @staticmethod
    def _filter_and_parse_entries(entries: List[Tuple[bytes | str, float]], cutoff_ts: float) -> List[Tuple[int, float]]:
        """Filter entries by timestamp and parse temperature data."""
        invalid_count = 0
        temperature_history = []
        for payload, score in entries:
            if score < cutoff_ts:
                continue
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
        try:
            station_icao = WeatherStatisticsRetriever._validate_station_input(station_icao)
            entries = await WeatherStatisticsRetriever._fetch_redis_entries(client, station_icao)

            if not entries:
                return []

            cutoff_ts = (get_current_utc() - timedelta(hours=hours)).timestamp()
            return WeatherStatisticsRetriever._filter_and_parse_entries(entries, cutoff_ts)

        except REDIS_ERRORS + (  # policy_guard: allow-silent-handler
            json.JSONDecodeError,
            ValueError,
            TypeError,
        ):
            logger.exception(f"Failed to get  temperature history: ")
            return []
