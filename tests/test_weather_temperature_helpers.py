import asyncio

import pytest

from common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.data_processor import (
    process_weather_results,
)
from common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.key_scanner import (
    KeyScanner,
)
from common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.station_scanner import (
    scan_weather_stations,
)
from common.optimized_status_reporter_helpers.weather_temperature_collector_helpers.temperature_extractor import (
    TemperatureExtractor,
)


class _FakeRedisScanner:
    def __init__(self, keys):
        self._keys = keys

    async def scan_iter(self, *, match=None, count=None):
        for key in self._keys:
            yield key


class _FakePipeline:
    def __init__(self, results):
        self._results = results
        self.commands = []

    def hgetall(self, key):
        self.commands.append(key)

    async def execute(self):
        return self._results


class _FakeRedisPipelineClient:
    def __init__(self, results):
        self._results = results
        self.pipelines_created = 0

    def pipeline(self):
        self.pipelines_created += 1
        return _FakePipeline(self._results)


@pytest.mark.asyncio
async def test_key_scanner_filters_invalid_keys():
    keys = [b"wx:abc", b"wx:good", b"wxbad", "wx:DEF", "wx:with:colon"]
    redis_client = _FakeRedisScanner(keys)

    weather_keys, station_codes = await KeyScanner.scan_weather_keys(redis_client, "wx:")

    assert weather_keys == [b"wx:abc", b"wx:good", "wx:DEF"]
    assert station_codes == ["ABC", "GOOD", "DEF"]


@pytest.mark.asyncio
async def test_station_scanner_collects_uppercase_codes():
    keys = [b"wx:abc", b"wx:def"]
    redis_client = _FakeRedisScanner(keys)

    weather_keys, station_codes = await scan_weather_stations(redis_client, "wx:")

    assert weather_keys == keys
    assert station_codes == ["ABC", "DEF"]


@pytest.mark.asyncio
async def test_temperature_extractor_builds_temperature_map():
    redis_client = _FakeRedisPipelineClient(
        [
            {"temp_f": 72, "weather_emoticon": "☀️"},
            {"temp_f": 68},  # default emoji fallback
        ]
    )
    weather_keys = ["wx:a", "wx:b"]
    station_codes = ["A", "B"]

    temperatures = await TemperatureExtractor.extract_temperatures(
        redis_client, weather_keys, station_codes
    )

    assert temperatures == {
        "A": {"temp_f": "72", "emoticon": "☀️"},
        "B": {"temp_f": "68", "emoticon": "🌡️"},
    }
    assert redis_client.pipelines_created == 1


def test_temperature_extractor_process_weather_data_handles_missing():
    assert TemperatureExtractor.process_weather_data(None) == {}
    assert TemperatureExtractor.process_weather_data({}) == {}
    assert TemperatureExtractor.process_weather_data({"temp_f": None}) == {}

    result = TemperatureExtractor.process_weather_data({"temp_f": 70, "weather_emoticon": "Rain"})
    assert result == {"temp_f": "70", "emoticon": "Rain"}


def test_process_weather_results_builds_mapping():
    station_codes = ["A", "B"]
    weather_results = [
        {"temp_f": 70, "weather_emoticon": "Cloudy"},
        {"temp_f": 65},
    ]

    result = process_weather_results(station_codes, weather_results)

    assert result == {
        "A": {"temp_f": "70", "emoticon": "Cloudy"},
        "B": {"temp_f": "65", "emoticon": "🌡️"},
    }
