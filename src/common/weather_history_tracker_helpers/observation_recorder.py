"""Temperature observation recording for weather history"""

import asyncio
import json
import logging

from redis.exceptions import RedisError

from common.exceptions import ValidationError
from common.redis_protocol.config import HISTORY_TTL_SECONDS
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


class WeatherObservationRecorder:
    """Records temperature observations to Redis sorted sets"""

    @staticmethod
    def validate_temperature_input(station_icao: object, temp_f: object):
        """
        Validate temperature recording inputs.

        Args:
            station_icao: Weather station ICAO code
            temp_f: Temperature in Fahrenheit

        Raises:
            ValueError: If inputs are invalid
        """
        if not station_icao or not isinstance(station_icao, str):
            raise ValidationError(f"Invalid station_icao: {station_icao}. Must be non-empty string.")
        if not isinstance(temp_f, (int, float)) or temp_f < _TEMP_MIN or temp_f > _TEMP_MAX:
            raise ValidationError(f"Invalid temperature: {temp_f}. Must be numeric between -200°F and 200°F.")

    @staticmethod
    def build_observation_payload(temp_f: float) -> tuple[str, int, str]:
        """
        Build observation payload for Redis storage.

        Args:
            temp_f: Temperature in Fahrenheit

        Returns:
            Tuple of (datetime_str, timestamp, json_payload)
        """
        current_utc = get_current_utc()
        datetime_str = current_utc.isoformat()
        timestamp = int(current_utc.timestamp())
        payload = json.dumps({"temp_f": temp_f, "observed_at": datetime_str})
        return datetime_str, timestamp, payload

    @staticmethod
    async def record_observation(client: RedisClient, station_icao: str, temp_f: float) -> tuple[bool, str]:
        """
        Record temperature observation to Redis sorted set.

        Args:
            client: Redis client instance
            station_icao: Weather station ICAO code (e.g., 'KAUS', 'KMDW')
            temp_f: Temperature in Fahrenheit

        Returns:
            Tuple of (success, datetime_str)
        """
        try:
            # Validate inputs
            WeatherObservationRecorder.validate_temperature_input(station_icao, temp_f)
            station_icao = ensure_uppercase_icao(station_icao)

            # Build payload
            datetime_str, timestamp, payload = WeatherObservationRecorder.build_observation_payload(temp_f)

            # Store in Redis
            redis_key = WeatherHistoryKey(icao=station_icao).key()
            await ensure_awaitable(client.zadd(redis_key, {payload: timestamp}))

            # Clean up old entries (keep only last 24 hours)
            await ensure_awaitable(client.zremrangebyscore(redis_key, "-inf", timestamp - HISTORY_TTL_SECONDS))

            # Set TTL for automatic cleanup
            await ensure_awaitable(client.expire(redis_key, HISTORY_TTL_SECONDS))

            logger.debug(f"Recorded {station_icao} temperature history: {temp_f:.1f}°F at {datetime_str}")

        except REDIS_ERRORS + (
            json.JSONDecodeError,
            ValueError,
            TypeError,
        ):
            logger.exception(f"Failed to record  temperature history: ")
            return False, ""
        else:
            return True, datetime_str
