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
    redis.zadd.assert_awaited_once_with(f"{HISTORY_KEY_PREFIX}kalshi", {"1700000000:12.5": 1_700_000_000})
    redis.expire.assert_awaited_once_with(f"{HISTORY_KEY_PREFIX}kalshi", HISTORY_TTL_SECONDS)


@pytest.mark.asyncio
async def test_record_service_update_failure(monkeypatch):
    redis = MagicMock()
    redis.zadd = AsyncMock(side_effect=RuntimeError("boom"))
    redis.expire = AsyncMock()
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_000)

    tracker = HistoryTracker()
    with pytest.raises(RuntimeError, match="Failed to record deribit history"):
        await tracker.record_service_update("deribit", 8.0)
    redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_get_service_history(monkeypatch):
    redis = MagicMock()
    redis.zrangebyscore = AsyncMock(return_value=[("1700000100:5.5", 1_700_000_100)])

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
    with pytest.raises(RuntimeError, match="Failed to load deribit history"):
        await tracker.get_service_history("deribit", hours=1)


# PriceHistoryTracker -------------------------------------------------------------
def _make_price_redis(*, zadd_result=1, expire_result=True, zrangebyscore_result: List[Tuple[str, float]] | None = None):
    redis = MagicMock()
    redis.close = AsyncMock(return_value=None)
    redis.pipeline = MagicMock(
        return_value=MagicMock(
            zadd=MagicMock(return_value=None),
            zremrangebyscore=MagicMock(return_value=None),
            expire=MagicMock(return_value=None),
            execute=AsyncMock(return_value=[zadd_result, 0, expire_result]),
        )
    )
    redis.zrangebyscore = AsyncMock(return_value=zrangebyscore_result or [])
    return redis


@pytest.mark.asyncio
async def test_record_price_update_success(monkeypatch):
    from common.price_history_utils import build_history_member

    redis = _make_price_redis()
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    fixed_now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: fixed_now)

    tracker = PriceHistoryTracker()
    result = await tracker.record_price_update("BTC", 45_000)

    assert result is True
    pipeline = redis.pipeline.return_value
    pipeline.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_price_update_handles_errors(monkeypatch):
    monkeypatch.setattr(
        "common.history_tracker.get_redis_connection",
        AsyncMock(side_effect=RuntimeError("down")),
    )
    fixed = datetime(2025, 1, 1, tzinfo=timezone.utc)
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
    from common.price_history_utils import build_history_member

    recent_dt = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    older_dt = recent_dt - timedelta(hours=1)
    cutoff_dt = recent_dt - timedelta(hours=4)

    recent_ts = int(recent_dt.timestamp())
    older_ts = int(older_dt.timestamp())
    old_ts = int((cutoff_dt - timedelta(hours=1)).timestamp())

    redis = _make_price_redis(
        zrangebyscore_result=[
            (build_history_member(older_ts, 44000.0).encode(), float(older_ts)),
            (build_history_member(recent_ts, 45000.0).encode(), float(recent_ts)),
        ]
    )

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
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
    ts1 = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp())
    redis = _make_price_redis(
        zrangebyscore_result=[
            (b"bad_member", float(ts1)),
        ]
    )
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    fixed = datetime(2025, 1, 2, tzinfo=timezone.utc)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: fixed)

    tracker = PriceHistoryTracker()
    with pytest.raises(ValueError):
        await tracker.get_price_history("ETH")


@pytest.mark.asyncio
async def test_get_price_history_handles_no_data(monkeypatch):
    redis = _make_price_redis(zrangebyscore_result=[])
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    fixed = datetime(2025, 1, 2, tzinfo=timezone.utc)
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
    zrangebyscore_result: List[Tuple[str, float]] = None,
) -> MagicMock:
    redis = MagicMock()
    redis.close = AsyncMock(return_value=None)
    redis.zadd = AsyncMock(return_value=zadd_result)
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)
    redis.zrange = AsyncMock(return_value=zrange_result or [])
    redis.zrangebyscore = AsyncMock(return_value=zrangebyscore_result or [])
    return redis


@pytest.mark.asyncio
async def test_record_temperature_update_success(monkeypatch):
    redis = _make_weather_redis()
    now = datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.weather_history_tracker_helpers.observation_recorder.get_current_utc", lambda: now)

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


@pytest.mark.asyncio
async def test_record_temperature_update_handles_errors(monkeypatch):
    redis = _make_weather_redis()
    redis.zadd = AsyncMock(side_effect=RuntimeError("fail"))

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    fixed_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr("common.weather_history_tracker_helpers.observation_recorder.get_current_utc", lambda: fixed_time)

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

    # zrangebyscore is called with cutoff = (now - 3h); mock returns only the in-window entry
    redis = _make_weather_redis(
        zrangebyscore_result=[
            (
                json.dumps({"temp_f": 70.0, "observed_at": recent_time.isoformat()}),
                recent_time.timestamp(),
            ),
        ]
    )

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.weather_history_tracker_helpers.statistics_retriever.get_current_utc", lambda: now)

    tracker = WeatherHistoryTracker()
    history = await tracker.get_temperature_history("KAUS", hours=3)

    assert history == [(int(recent_time.timestamp()), 70.0)]


@pytest.mark.asyncio
async def test_get_temperature_history_skips_invalid_entries(monkeypatch):
    now = datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc)
    redis = _make_weather_redis(
        zrangebyscore_result=[
            (b"not-json", now.timestamp()),
            (json.dumps({"no_temp": 10}), now.timestamp()),
        ]
    )

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.weather_history_tracker_helpers.statistics_retriever.get_current_utc", lambda: now)

    tracker = WeatherHistoryTracker()
    history = await tracker.get_temperature_history("KAUS")
    assert history == []


@pytest.mark.asyncio
async def test_get_temperature_history_validates_station():
    tracker = WeatherHistoryTracker()
    with pytest.raises(ValueError):
        await tracker.get_temperature_history("")


# BalanceHistoryTracker -----------------------------------------------------------
from common.history_tracker import BalanceHistoryTracker
from common.redis_protocol.config import BALANCE_KEY_PREFIX


def _make_balance_redis(
    *,
    zadd_result=1,
    zrangebyscore_result: List[Tuple[str, float]] | None = None,
    zrange_result: List[Tuple[str, float]] | None = None,
) -> MagicMock:
    redis = MagicMock()
    redis.close = AsyncMock(return_value=None)
    redis.zadd = AsyncMock(return_value=zadd_result)
    redis.zrangebyscore = AsyncMock(return_value=zrangebyscore_result or [])
    redis.zrange = AsyncMock(return_value=zrange_result or [])
    return redis


@pytest.mark.asyncio
async def test_balance_record_success(monkeypatch):
    redis = _make_balance_redis()
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_000)

    tracker = BalanceHistoryTracker()
    result = await tracker.record_balance("kalshi", 123456)

    assert result is True
    redis.zadd.assert_awaited_once_with(f"{BALANCE_KEY_PREFIX}kalshi", {"1700000000:123456": 1_700_000_000})


@pytest.mark.asyncio
async def test_balance_record_handles_redis_error(monkeypatch):
    redis = _make_balance_redis()
    redis.zadd = AsyncMock(side_effect=RuntimeError("redis down"))

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_000)

    tracker = BalanceHistoryTracker()
    with pytest.raises(RuntimeError, match="Failed to record kalshi balance"):
        await tracker.record_balance("kalshi", 100)


@pytest.mark.asyncio
async def test_balance_get_history_with_hours(monkeypatch):
    redis = _make_balance_redis(
        zrangebyscore_result=[
            ("1700000100:50000", 1_700_000_100),
            ("1700000200:60000", 1_700_000_200),
        ]
    )
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_300)

    tracker = BalanceHistoryTracker()
    history = await tracker.get_balance_history("kalshi", hours=1)

    assert history == [(1_700_000_100, 50000), (1_700_000_200, 60000)]
    redis.zrangebyscore.assert_awaited_once()


@pytest.mark.asyncio
async def test_balance_get_history_all(monkeypatch):
    redis = _make_balance_redis(
        zrange_result=[
            ("1600000000:40000", 1_600_000_000),
            ("1700000100:50000", 1_700_000_100),
        ]
    )
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_300)

    tracker = BalanceHistoryTracker()
    history = await tracker.get_balance_history("kalshi", hours=None)

    assert history == [(1_600_000_000, 40000), (1_700_000_100, 50000)]
    redis.zrange.assert_awaited_once_with(f"{BALANCE_KEY_PREFIX}kalshi", 0, -1, withscores=True)


@pytest.mark.asyncio
async def test_balance_get_history_handles_redis_error(monkeypatch):
    redis = _make_balance_redis()
    redis.zrangebyscore = AsyncMock(side_effect=RuntimeError("redis down"))

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_300)

    tracker = BalanceHistoryTracker()
    with pytest.raises(RuntimeError, match="Failed to load kalshi balance history"):
        await tracker.get_balance_history("kalshi", hours=1)


@pytest.mark.asyncio
async def test_balance_ensure_client_raises_on_none(monkeypatch):
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=None))

    tracker = BalanceHistoryTracker()
    with pytest.raises(RuntimeError, match="Failed to record kalshi balance"):
        await tracker.record_balance("kalshi", 100)


@pytest.mark.asyncio
async def test_history_tracker_ensure_client_raises_on_none(monkeypatch):
    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=None))

    tracker = HistoryTracker()
    with pytest.raises(RuntimeError, match="Failed to record kalshi history"):
        await tracker.record_service_update("kalshi", 10.0)


@pytest.mark.asyncio
async def test_get_service_history_handles_value_error(monkeypatch):
    redis = MagicMock()
    redis.zrangebyscore = AsyncMock(return_value=[("invalid", "not-a-number")])

    monkeypatch.setattr("common.history_tracker.get_redis_connection", AsyncMock(return_value=redis))
    monkeypatch.setattr("common.history_tracker.time.time", lambda: 1_700_000_200)

    tracker = HistoryTracker()
    with pytest.raises((ValueError, TypeError)):
        await tracker.get_service_history("kalshi", hours=1)
