from __future__ import annotations

import logging
import types
from typing import Any, Dict, List, Tuple

import pytest

from common.config.weather import WeatherConfigError
from common.redis_protocol.kalshi_store import KalshiStore
from common.redis_protocol.market_normalization import format_probability_value
from common.redis_protocol.market_normalization_core import ProbabilityValueError
from common.redis_protocol.weather_station_resolver import WeatherStationResolver


class _FakeRedis:
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}
        self.pipeline_calls: List[Tuple[str, Tuple[Any, ...]]] = []

    async def hgetall(self, key: str):
        return self.store.get(key, {})

    def pipeline(self):
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, redis: _FakeRedis):
        self.redis = redis
        self.commands: List[Tuple[str, Tuple[Any, ...]]] = []

    def hset(self, key: str, field: str, value: str):
        self.commands.append(("hset", (key, field, value)))
        self.redis.pipeline_calls.append(("hset", (key, field, value)))
        self.redis.store.setdefault(key, {})[field] = value
        return self

    def hdel(self, key: str, *fields: str):
        self.commands.append(("hdel", (key, fields)))
        self.redis.pipeline_calls.append(("hdel", (key, fields)))
        for field in fields:
            self.redis.store.setdefault(key, {}).pop(field, None)
        return self

    async def execute(self):
        return True


def _basic_store(redis: _FakeRedis | None = None) -> KalshiStore:
    redis_client = redis or _FakeRedis()
    resolver = WeatherStationResolver(
        lambda: {"nyc": {"icao": "KNYC"}},
        logger=logging.getLogger("tests.runtime"),
    )
    store = KalshiStore(
        redis=redis_client,
        weather_resolver=resolver,
    )
    store.redis = redis_client
    store._initialized = True

    async def always_connected(self) -> bool:
        return True

    store._ensure_redis_connection = types.MethodType(always_connected, store)  # type: ignore[assignment]
    return store


def test_kalshi_store_handles_mapping_loader_failure(monkeypatch):
    def failing_loader():
        raise WeatherConfigError("missing mapping")

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.store._default_weather_station_loader",
        failing_loader,
    )
    with pytest.raises(WeatherConfigError):
        KalshiStore()


@pytest.mark.asyncio
async def test_get_market_snapshot_by_key_invalid_raises():
    store = _basic_store()
    with pytest.raises(TypeError):
        await store.get_market_snapshot_by_key("invalid-key")


def test_format_probability_value_rejects_non_finite():
    with pytest.raises(ProbabilityValueError):
        format_probability_value(float("nan"))


@pytest.mark.asyncio
async def test_update_interpolation_results_pipeline(monkeypatch):
    redis = _FakeRedis()
    store = _basic_store(redis)
    market_ticker = "KXHIGH-20240101-KNYC-BETWEEN-70-90"
    market_key = store.get_market_key(market_ticker)
    redis.store[market_key] = {"t_yes_bid": "10"}

    async def get_redis(self):
        assert self.redis is not None
        return self.redis

    store._get_redis = types.MethodType(get_redis, store)  # type: ignore[assignment]

    mapping_results = {
        market_ticker: {
            "t_yes_bid": 15.0,
            "t_yes_ask": 25.0,
            "interpolation_method": "fast_gp",
            "deribit_points_used": 12,
            "interpolation_quality_score": 0.99,
        }
    }

    success = await store.update_interpolation_results("BTC", mapping_results)
    assert success is True
    assert redis.store[market_key]["t_yes_bid"] == "15.0"
    assert redis.store[market_key]["interpolation_method"] == "fast_gp"
    assert any(cmd[0] == "hset" for cmd in redis.pipeline_calls)
