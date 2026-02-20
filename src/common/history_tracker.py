"""
Async history tracker for monitoring service performance and price data

Tracks updates per second for each service and BTC/ETH price history, storing data in Redis
with automatic 24-hour expiration:
- history:kalshi (sorted set)
- history:deribit (sorted set)
- history:btc (hash with datetime as field, price as value)
- history:eth (hash with datetime as field, price as value)
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from common.exceptions import ValidationError
from common.redis_protocol.config import BALANCE_KEY_PREFIX, HISTORY_KEY_PREFIX, HISTORY_TTL_SECONDS
from common.redis_protocol.error_types import REDIS_ERRORS as _BASE_REDIS_ERRORS
from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.redis_utils import RedisOperationError, get_redis_connection

logger = logging.getLogger(__name__)

_BALANCE_MEMBER_PARTS = 2  # "timestamp:balance_cents" → exactly 2 colon-separated parts
_HISTORY_MEMBER_PARTS = 2  # "timestamp:value" → exactly 2 colon-separated parts


def _parse_history_member(member_str: str) -> float:
    """Parse value from a history member string 'timestamp:value'."""
    parts = member_str.split(":", 1)
    if len(parts) != _HISTORY_MEMBER_PARTS:
        raise ValueError(f"Unexpected member format: {member_str!r}")
    return float(parts[1])


def _parse_balance_member(member_str: str) -> int:
    """Parse balance_cents from a balance member string 'timestamp:balance_cents'."""
    parts = member_str.split(":", 1)
    if len(parts) != _BALANCE_MEMBER_PARTS:
        raise ValueError(f"Unexpected member format: {member_str!r}")
    return int(parts[1])


# OSError (in _BASE_REDIS_ERRORS) is the parent of ConnectionError and TimeoutError,
# so those are already covered. RedisOperationError is raised by redis_utils helpers.
REDIS_ERRORS = _BASE_REDIS_ERRORS + (RedisOperationError,)


@dataclass
class HistoryDataPoint:
    """Single history data point with timestamp and value"""

    timestamp: int
    value: float


class HistoryTracker:
    """Async history tracker for monitoring service performance."""

    def __init__(self):
        self.redis_client: Optional[RedisClient] = None

    async def _ensure_client(self) -> RedisClient:
        if self.redis_client is None:
            self.redis_client = await get_redis_connection()
        if self.redis_client is None:
            raise ConnectionError("Redis client not initialized for HistoryTracker")
        return self.redis_client

    async def record_service_update(self, service_name: str, updates_per_second: float) -> bool:
        """Record the service update stream."""
        try:
            client = await self._ensure_client()
            current_timestamp = int(time.time())
            redis_key = f"{HISTORY_KEY_PREFIX}{service_name}"
            member = f"{current_timestamp}:{updates_per_second}"
            await ensure_awaitable(client.zadd(redis_key, {member: current_timestamp}))
            await ensure_awaitable(client.expire(redis_key, HISTORY_TTL_SECONDS))
            logger.debug(
                "Recorded %s history: %s updates/sec at %s",
                service_name,
                updates_per_second,
                current_timestamp,
            )
        except REDIS_ERRORS as exc:
            logger.exception("Failed to record %s history", service_name)
            raise RuntimeError(f"Failed to record {service_name} history in Redis") from exc
        else:
            return True

    async def get_service_history(self, service_name: str, hours: int = 24) -> List[Tuple[int, float]]:
        """Retrieve the stored service history data."""
        try:
            client = await self._ensure_client()
            redis_key = f"{HISTORY_KEY_PREFIX}{service_name}"
            current_time = int(time.time())
            start_time = current_time - (hours * 3600)
            data = await ensure_awaitable(client.zrangebyscore(redis_key, start_time, current_time, withscores=True))
            history_data = []
            for member, score in data:
                timestamp = int(score)
                member_str = member.decode() if isinstance(member, bytes) else str(member)
                value = _parse_history_member(member_str)
                history_data.append((timestamp, value))
        except REDIS_ERRORS as exc:
            logger.exception("Failed to get %s history", service_name)
            raise RuntimeError(f"Failed to load {service_name} history from Redis") from exc
        except (ValueError, TypeError):
            logger.exception("Invalid %s history payload", service_name)
            raise
        else:
            return history_data


class PriceHistoryTracker:
    """
    Slim coordinator for BTC and ETH price history tracking

    Delegates connection management, price recording, and history retrieval
    to focused helper modules while maintaining the public API.

    Stores price data in Redis hash with automatic 24-hour expiration:
    - history:btc (hash with datetime as field, price as value)
    - history:eth (hash with datetime as field, price as value)
    """

    def __init__(self):
        """Initialize price history tracker with helper delegation"""
        from .price_history_connection_manager import PriceHistoryConnectionManager
        from .price_history_recorder import PriceHistoryRecorder
        from .price_history_retriever import PriceHistoryRetriever

        self._connection_manager = PriceHistoryConnectionManager(get_redis_connection)
        self._recorder = PriceHistoryRecorder()
        self._retriever = PriceHistoryRetriever()

    async def initialize(self):
        """Initialize Redis connection"""
        await self._connection_manager.initialize()

    async def cleanup(self):
        """Clean up Redis connection to prevent resource leaks"""
        await self._connection_manager.cleanup()

    async def record_price_update(self, currency: str, price: float) -> bool:
        """
        Record price update for BTC or ETH in Redis hash structure

        Args:
            currency: Currency symbol ('BTC' or 'ETH')
            price: Price in USD

        Returns:
            True if recorded successfully, False otherwise

        Raises:
            ValueError: If currency is not 'BTC' or 'ETH'
            ValueError: If price is not positive
        """
        try:
            await self._connection_manager.ensure_connected()
            client = self._connection_manager.get_client()
            success, _ = await self._recorder.record_price(client, currency, price)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        except (RuntimeError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Failed to record {currency} price history") from exc
        else:
            return success

    async def get_price_history(self, currency: str, hours: int = 24) -> List[Tuple[int, float]]:
        """
        Get price history for currency from Redis hash structure

        Args:
            currency: Currency symbol ('BTC' or 'ETH')
            hours: Number of hours of history to retrieve

        Returns:
            List of (timestamp, price) tuples sorted by timestamp

        Raises:
            ValueError: If currency is not 'BTC' or 'ETH'
        """
        try:
            await self._connection_manager.ensure_connected()
            client = self._connection_manager.get_client()
            return await self._retriever.get_history(client, currency, hours)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc


class WeatherHistoryTracker:
    """
    Slim coordinator for weather station temperature history tracking.

    Delegates connection management, observation recording, and statistics
    retrieval to focused helper modules while maintaining the public API.
    """

    def __init__(self):
        """Initialize weather history tracker with helper delegation"""
        from .weather_history_tracker_helpers import (
            WeatherHistoryConnectionManager,
            WeatherObservationRecorder,
            WeatherStatisticsRetriever,
        )

        self._connection_manager = WeatherHistoryConnectionManager(get_redis_connection)
        self._observation_recorder = WeatherObservationRecorder()
        self._statistics_retriever = WeatherStatisticsRetriever()

    async def initialize(self):
        """Initialize Redis connection"""
        await self._connection_manager.initialize()

    async def cleanup(self):
        """Clean up Redis connection to prevent resource leaks"""
        await self._connection_manager.cleanup()

    async def record_temperature_update(self, station_icao: str, temp_f: float) -> bool:
        """
        Record temperature updates in the weather station history sorted set.

        Args:
            station_icao: Weather station ICAO code (e.g., 'KAUS', 'KMDW')
            temp_f: Temperature in Fahrenheit

        Returns:
            True if recorded successfully

        Raises:
            ValueError: If station_icao is empty or temp_f is invalid
            REDIS_ERRORS: If a Redis connection or command error occurs
        """
        try:
            self._observation_recorder.validate_temperature_input(station_icao, temp_f)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

        try:
            await self._connection_manager.ensure_connected()
            client = self._connection_manager.get_client()
            success, _ = await self._observation_recorder.record_observation(client, station_icao, temp_f)
        except REDIS_ERRORS:
            logger.exception("Failed to record temperature for %s", station_icao)
            raise
        else:
            return success

    async def get_temperature_history(self, station_icao: str, hours: int = 24) -> List[Tuple[int, float]]:
        """
        Get temperature history for a weather station from the sorted-set history store.

        Args:
            station_icao: Weather station ICAO code (e.g., 'KAUS', 'KMDW')
            hours: Number of hours of history to retrieve

        Returns:
            List of (timestamp, temp_f) tuples sorted by timestamp

        Raises:
            ValueError: If station_icao is empty
        """
        try:
            await self._connection_manager.ensure_connected()
            client = self._connection_manager.get_client()
            return await self._statistics_retriever.get_history(client, station_icao, hours)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        except REDIS_ERRORS as exc:
            raise RuntimeError(f"Failed to get temperature history for {station_icao}") from exc


class BalanceHistoryTracker:
    """
    Tracker for account balance history.

    Stores balance data in Redis sorted set with NO expiration for permanent history:
    - balance:kalshi (sorted set with timestamp as score, balance_cents as member)
    """

    def __init__(self):
        """Initialize balance history tracker."""
        self.redis_client: Optional[RedisClient] = None

    async def _ensure_client(self) -> RedisClient:
        """Ensure Redis client is connected."""
        if self.redis_client is None:
            self.redis_client = await get_redis_connection()
        if self.redis_client is None:
            raise ConnectionError("Redis client not initialized for BalanceHistoryTracker")
        return self.redis_client

    async def record_balance(self, exchange: str, balance_cents: int) -> bool:
        """
        Record account balance in Redis sorted set.

        Args:
            exchange: Exchange name (e.g., 'kalshi')
            balance_cents: Account balance in cents

        Returns:
            True if recorded successfully

        Raises:
            RuntimeError: If Redis operation fails
        """
        try:
            client = await self._ensure_client()
            current_timestamp = int(time.time())
            redis_key = f"{BALANCE_KEY_PREFIX}{exchange}"
            # Use timestamp:balance as member for unique entries, timestamp as score for time queries
            member = f"{current_timestamp}:{balance_cents}"
            await ensure_awaitable(client.zadd(redis_key, {member: current_timestamp}))
            logger.debug(
                "Recorded %s balance: %d cents at %s",
                exchange,
                balance_cents,
                current_timestamp,
            )
        except REDIS_ERRORS as exc:
            logger.exception("Failed to record %s balance", exchange)
            raise RuntimeError(f"Failed to record {exchange} balance in Redis") from exc
        else:
            return True

    async def get_balance_history(self, exchange: str, hours: Optional[int] = None) -> List[Tuple[int, int]]:
        """
        Get balance history from Redis sorted set.

        Args:
            exchange: Exchange name (e.g., 'kalshi')
            hours: Number of hours of history to retrieve (None for all history)

        Returns:
            List of (timestamp, balance_cents) tuples sorted by timestamp
        """
        try:
            client = await self._ensure_client()
            redis_key = f"{BALANCE_KEY_PREFIX}{exchange}"
            current_time = int(time.time())

            if hours is not None:
                start_time = current_time - (hours * 3600)
                data = await ensure_awaitable(client.zrangebyscore(redis_key, start_time, current_time, withscores=True))
            else:
                data = await ensure_awaitable(client.zrange(redis_key, 0, -1, withscores=True))

            history_data = []
            for member, score in data:
                timestamp = int(score)
                # Parse member format: "timestamp:balance_cents"
                member_str = member.decode() if isinstance(member, bytes) else str(member)
                history_data.append((timestamp, _parse_balance_member(member_str)))
        except (ValueError, TypeError):
            logger.exception("Invalid %s balance history payload", exchange)
            raise
        except REDIS_ERRORS as exc:
            logger.exception("Failed to get %s balance history", exchange)
            raise RuntimeError(f"Failed to load {exchange} balance history from Redis") from exc
        else:
            return history_data
