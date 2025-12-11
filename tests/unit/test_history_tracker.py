from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.history_tracker import (
    HISTORY_KEY_PREFIX,
    HISTORY_TTL_SECONDS,
    HistoryTracker,
    PriceHistoryTracker,
    WeatherHistoryTracker,
)

_VAL_72_5 = 72.5

from common.redis_schema import WeatherHistoryKey


# HistoryTracker -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_record_service_update_success(monkeypatch):
    redis = MagicMock()
    redis.zadd = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_000)

    tracker = HistoryTracker()
    result = await tracker.record_service_update("kalshi", 12.5)

    assert result is True
    redis.zadd.assert_awaited_once_with(f"{HISTORY_KEY_PREFIX}kalshi", {"1700000000": 12.5})
    redis.expire.assert_awaited_once_with(f"{HISTORY_KEY_PREFIX}kalshi", HISTORY_TTL_SECONDS)


@pytest.mark.asyncio
async def test_record_service_update_failure(monkeypatch):
    redis = MagicMock()
    redis.zadd = AsyncMock(side_effect=RuntimeError("boom"))
    redis.expire = AsyncMock()
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_000)

    tracker = HistoryTracker()
    tracker = HistoryTracker()
    with pytest.raises(RuntimeError, match="Failed to record deribit history"):
        await tracker.record_service_update("deribit", 8.0)
    redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_get_service_history(monkeypatch):
    redis = MagicMock()
    redis.zrangebyscore = AsyncMock(return_value=[("5.5", 1_700_000_100)])

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_200)

    tracker = HistoryTracker()
    history = await tracker.get_service_history("kalshi", hours=1)

    assert history == [(1_700_000_100, 5.5)]
    redis.zrangebyscore.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_service_history_handles_error(monkeypatch):
    redis = MagicMock()
    redis.zrangebyscore = AsyncMock(side_effect=RuntimeError("no redis"))

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_200)

    tracker = HistoryTracker()
    tracker = HistoryTracker()
    with pytest.raises(RuntimeError, match="Failed to load deribit history"):
        await tracker.get_service_history("deribit", hours=1)


# PriceHistoryTracker -------------------------------------------------------------
def _make_price_redis(*, hset_result=1, expire_result=True, hgetall_result: Dict[str, str] | Dict[bytes, bytes] = None):
    redis = MagicMock()
    redis.close = AsyncMock(return_value=None)
    redis.hset = AsyncMock(return_value=hset_result)
    redis.expire = AsyncMock(return_value=expire_result)
    redis.hgetall = AsyncMock(return_value=hgetall_result or {})
    return redis


@pytest.mark.asyncio
async def test_record_price_update_success(monkeypatch):
    redis = _make_price_redis()
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    fixed_now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("common.history_tracker.get_current_utc", lambda: fixed_now)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: fixed_now)

    tracker = PriceHistoryTracker()
    result = await tracker.record_price_update("BTC", 45_000)

    assert result is True
    field = fixed_now.isoformat()
    redis.hset.assert_awaited_once_with("history:btc", field, "45000.0")
    redis.expire.assert_awaited_once_with("history:btc", HISTORY_TTL_SECONDS)


@pytest.mark.asyncio
async def test_record_price_update_handles_errors(monkeypatch):
    monkeypatch.setattr(
        "common.history_tracker.get_redis_connection",
        AsyncMock(side_effect=RuntimeError("down")),
    )
    fixed = datetime(2025, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr("common.history_tracker.get_current_utc", lambda: fixed)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: fixed)

    tracker = PriceHistoryTracker()
    with pytest.raises(RuntimeError, match="Failed to record BTC price history"):
        await tracker.record_price_update("BTC", 42_000)


@pytest.mark.asyncio
async def test_record_price_update_validates_inputs():
    tracker = PriceHistoryTracker()

    with pytest.raises(ValueError):
        await tracker.record_price_update("DOGE", 1.0)

    with pytest.raises(ValueError):
        await tracker.record_price_update("BTC", -10.0)


@pytest.mark.asyncio
async def test_get_price_history_filters_and_sorts(monkeypatch):
    recent_dt = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    older_dt = recent_dt - timedelta(hours=1)
    cutoff_dt = recent_dt - timedelta(hours=4)

    redis = _make_price_redis(
        hgetall_result={
            recent_dt.isoformat(): "45000",
            older_dt.isoformat(): "44000",
            (cutoff_dt - timedelta(hours=1)).isoformat(): "43000",  # should be filtered out
        }
    )

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.get_current_utc", lambda: recent_dt)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: recent_dt)

    tracker = PriceHistoryTracker()
    history = await tracker.get_price_history("BTC", hours=3)

    expected = [
        (int(older_dt.timestamp()), 44000.0),
        (int(recent_dt.timestamp()), 45000.0),
    ]
    assert history == expected


@pytest.mark.asyncio
async def test_get_price_history_skips_invalid_entries(monkeypatch):
    redis = _make_price_redis(
        hgetall_result={
            "not-a-date": "100",
            datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(): "NaN",
        }
    )
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    fixed = datetime(2025, 1, 2, tzinfo=timezone.utc)
    monkeypatch.setattr("common.history_tracker.get_current_utc", lambda: fixed)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: fixed)

    tracker = PriceHistoryTracker()
    history = await tracker.get_price_history("ETH")
    assert history == []


@pytest.mark.asyncio
async def test_get_price_history_handles_no_data(monkeypatch):
    redis = _make_price_redis(hgetall_result={})
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    fixed = datetime(2025, 1, 2, tzinfo=timezone.utc)
    monkeypatch.setattr("common.history_tracker.get_current_utc", lambda: fixed)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: fixed)

    tracker = PriceHistoryTracker()
    history = await tracker.get_price_history("BTC")
    assert history == []


@pytest.mark.asyncio
async def test_get_price_history_validates_currency():
    tracker = PriceHistoryTracker()
    with pytest.raises(ValueError):
        await tracker.get_price_history("DOGE")


# WeatherHistoryTracker -----------------------------------------------------------
def _make_weather_redis(
    *,
    zadd_result=1,
    zrange_result: List[Tuple[str, float]] = None,
) -> MagicMock:
    redis = MagicMock()
    redis.close = AsyncMock(return_value=None)
    redis.zadd = AsyncMock(return_value=zadd_result)
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)
    redis.zrange = AsyncMock(return_value=zrange_result or [])
    return redis


@pytest.mark.asyncio
async def test_record_temperature_update_success(monkeypatch):
    redis = _make_weather_redis()
    now = datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.get_current_utc", lambda: now)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: now)

    tracker = WeatherHistoryTracker()
    result = await tracker.record_temperature_update("KAUS", 72.5)

    assert result is True
    zadd_args = redis.zadd.await_args.args  # type: ignore[attr-defined]
    assert zadd_args[0] == WeatherHistoryKey(icao="KAUS").key()
    payload = zadd_args[1]
    assert isinstance(payload, dict) and len(payload) == 1
    payload_json = next(iter(payload.keys()))
    decoded = json.loads(payload_json)
    assert decoded["temp_f"] == _VAL_72_5
    assert decoded["observed_at"] == now.isoformat()
    redis.expire.assert_awaited_once_with(zadd_args[0], HISTORY_TTL_SECONDS)


@pytest.mark.asyncio
async def test_record_temperature_update_handles_errors(monkeypatch):
    redis = _make_weather_redis()
    redis.zadd = AsyncMock(side_effect=RuntimeError("fail"))

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    fixed_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr("common.history_tracker.get_current_utc", lambda: fixed_time)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: fixed_time)

    tracker = WeatherHistoryTracker()
    result = await tracker.record_temperature_update("KAUS", 70.0)
    assert result is False


@pytest.mark.asyncio
async def test_record_temperature_update_validates_inputs():
    tracker = WeatherHistoryTracker()
    with pytest.raises(ValueError):
        await tracker.record_temperature_update("", 70.0)
    with pytest.raises(ValueError):
        await tracker.record_temperature_update("KAUS", 250.0)


@pytest.mark.asyncio
async def test_get_temperature_history_filters(monkeypatch):
    now = datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc)
    recent_time = now - timedelta(hours=1)
    old_time = now - timedelta(hours=5)

    redis = _make_weather_redis(
        zrange_result=[
            (
                json.dumps({"temp_f": 70.0, "observed_at": recent_time.isoformat()}),
                recent_time.timestamp(),
            ),
            (
                json.dumps({"temp_f": 65.0, "observed_at": old_time.isoformat()}),
                old_time.timestamp(),
            ),
        ]
    )

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.get_current_utc", lambda: now)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: now)

    tracker = WeatherHistoryTracker()
    history = await tracker.get_temperature_history("KAUS", hours=3)

    assert history == [(int(recent_time.timestamp()), 70.0)]


@pytest.mark.asyncio
async def test_get_temperature_history_skips_invalid_entries(monkeypatch):
    now = datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc)
    redis = _make_weather_redis(
        zrange_result=[
            (b"not-json", now.timestamp()),
            (json.dumps({"no_temp": 10}), now.timestamp()),
        ]
    )

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.get_current_utc", lambda: now)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: now)

    tracker = WeatherHistoryTracker()
    history = await tracker.get_temperature_history("KAUS")
    assert history == []


@pytest.mark.asyncio
async def test_get_temperature_history_validates_station():
    tracker = WeatherHistoryTracker()
    with pytest.raises(ValueError):
        await tracker.get_temperature_history("")
