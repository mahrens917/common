"""Tests for weather_temperature_collector module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

from common.optimized_status_reporter_helpers.weather_temperature_collector import (
    WeatherTemperatureCollector,
)


class TestWeatherTemperatureCollector:
    """Tests for WeatherTemperatureCollector class."""

    def test_init_stores_redis_client(self):
        """WeatherTemperatureCollector should store redis_client reference."""
        redis_client = MagicMock()
        collector = WeatherTemperatureCollector(redis_client)
        assert collector.redis_client is redis_client

    def test_init_defaults_to_none_redis_client(self):
        """WeatherTemperatureCollector should default redis_client to None."""
        collector = WeatherTemperatureCollector()
        assert collector.redis_client is None


class TestCollectWeatherTemperatures:
    """Tests for collect_weather_temperatures method."""

    @pytest.mark.asyncio
    async def test_raises_on_redis_timeout(self):
        """collect_weather_temperatures should raise on Redis timeout."""
        redis_client = MagicMock()
        redis_client.scan_iter = MagicMock(side_effect=RedisTimeoutError("Timeout"))
        collector = WeatherTemperatureCollector(redis_client)
        with pytest.raises(RedisTimeoutError):
            await collector.collect_weather_temperatures()

    @pytest.mark.asyncio
    async def test_raises_on_redis_error(self):
        """collect_weather_temperatures should raise on RedisError."""
        redis_client = MagicMock()
        redis_client.scan_iter = MagicMock(side_effect=RedisError("Connection lost"))
        collector = WeatherTemperatureCollector(redis_client)
        with pytest.raises(RedisError):
            await collector.collect_weather_temperatures()

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_keys_found(self):
        """collect_weather_temperatures should return empty dict when no keys exist."""
        redis_client = MagicMock()

        async def empty_iter(*args, **kwargs):
            return
            yield  # Make it an async generator but don't yield anything

        redis_client.scan_iter = empty_iter
        collector = WeatherTemperatureCollector(redis_client)
        result = await collector.collect_weather_temperatures()
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_temperature_data_on_success(self):
        """collect_weather_temperatures should return temperature data on success."""
        redis_client = MagicMock()

        async def mock_scan_iter(*args, **kwargs):
            yield b"station:KJFK"

        redis_client.scan_iter = mock_scan_iter

        pipeline = MagicMock()
        pipeline.hgetall = MagicMock()
        pipeline.execute = AsyncMock(return_value=[{b"temp_f": b"72.5", b"weather_emoticon": "sunny"}])
        redis_client.pipeline = MagicMock(return_value=pipeline)

        collector = WeatherTemperatureCollector(redis_client)

        with patch("common.optimized_status_reporter_helpers.weather_temperature_collector.WeatherStationKey") as mock_key_class:
            mock_key = MagicMock()
            mock_key.key.return_value = "station:TEST"
            mock_key_class.return_value = mock_key

            result = await collector.collect_weather_temperatures()

        assert "KJFK" in result
        assert result["KJFK"]["temp_f"] == "72.5"
