import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from common.websocket.message_stats_collector import MessageStatsCollector

_TEST_COUNT_2 = 2
_TEST_COUNT_3 = 3
_TEST_COUNT_5 = 5
_VAL_2_0 = 2.0


class FakePipeline:
    def __init__(self, client):
        self._client = client
        self._commands = []

    def zremrangebyscore(self, key, min_score, max_score):
        self._commands.append(("zremrangebyscore", key, min_score, max_score))

    def zadd(self, key, mapping):
        for member, score in mapping.items():
            self._client.history.setdefault(key, {})[member] = score
        self._commands.append(("zadd", key, mapping))

    def expire(self, key, seconds):
        self._client.expire_calls.append((key, seconds))
        self._commands.append(("expire", key, seconds))

    async def execute(self):
        return [True] * len(self._commands)


class FakeRedisClient:
    def __init__(self):
        self.history = {}
        self.expire_calls = []

    def pipeline(self):
        return FakePipeline(self)


def test_add_message_increments_count():
    collector = MessageStatsCollector("kalshi")
    collector.add_message()
    collector.add_message()
    assert collector._message_count == _TEST_COUNT_2


@pytest.mark.asyncio
async def test_check_and_record_rate_updates_state(monkeypatch):
    collector = MessageStatsCollector("kalshi")
    collector._message_count = _TEST_COUNT_5
    collector._last_rate_time = 0

    monkeypatch.setattr("common.websocket.message_stats_collector.time.time", lambda: 2.0)

    collector._check_silent_failure = AsyncMock()
    collector._write_to_history_redis = AsyncMock()

    await collector.check_and_record_rate()

    assert collector.current_rate == _TEST_COUNT_5
    assert collector._message_count == 0
    assert collector._last_rate_time == _VAL_2_0
    collector._check_silent_failure.assert_awaited_once_with(2.0)
    collector._write_to_history_redis.assert_awaited_once_with(_TEST_COUNT_5, 2.0)


@pytest.mark.asyncio
async def test_check_and_record_rate_skips_within_interval():
    collector = MessageStatsCollector("kalshi")
    collector._message_count = _TEST_COUNT_3
    collector._last_rate_time = time.time()

    await collector.check_and_record_rate()

    assert collector._message_count == _TEST_COUNT_3


@pytest.mark.asyncio
async def test_check_silent_failure_triggers_alert(dummy_alerts):
    collector = MessageStatsCollector("kalshi", silent_failure_threshold_seconds=10)
    collector.current_rate = 0
    collector._last_nonzero_update_time = 0

    with pytest.raises(ConnectionError):
        await collector._check_silent_failure(current_time=20)

    assert dummy_alerts  # alert emitted


@pytest.mark.asyncio
async def test_check_silent_failure_no_alert_when_messages_recent():
    collector = MessageStatsCollector("kalshi", silent_failure_threshold_seconds=10)
    collector.current_rate = 0
    collector._last_nonzero_update_time = 15

    await collector._check_silent_failure(current_time=20)


@pytest.mark.asyncio
async def test_write_to_history_redis_records_data(monkeypatch):
    collector = MessageStatsCollector("kalshi")
    fake_client = FakeRedisClient()

    async def fake_get_connection():
        return fake_client

    monkeypatch.setattr(
        "common.websocket.message_stats_collector.get_redis_connection",
        fake_get_connection,
    )

    timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()
    await collector._write_to_history_redis(7, timestamp)

    history_key = "history:kalshi"
    assert history_key in fake_client.history
    assert len(fake_client.history[history_key]) == 1
    assert fake_client.expire_calls == []


@pytest.mark.asyncio
async def test_write_to_history_redis_raises_on_failure(monkeypatch):
    collector = MessageStatsCollector("kalshi")

    class BrokenPipeline:
        def zremrangebyscore(self, *a):
            pass

        def zadd(self, *a):
            pass

        def expire(self, *a):
            pass

        async def execute(self):
            raise RuntimeError("boom")

    class BrokenRedis(FakeRedisClient):
        def pipeline(self):
            return BrokenPipeline()

    fake_client = BrokenRedis()

    async def fake_get_connection():
        return fake_client

    monkeypatch.setattr(
        "common.websocket.message_stats_collector.get_redis_connection",
        fake_get_connection,
    )

    with pytest.raises(ConnectionError):
        await collector._write_to_history_redis(1, 0)
