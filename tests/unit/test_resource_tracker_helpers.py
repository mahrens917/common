from __future__ import annotations

import asyncio

import pytest

from common.resource_tracker import ResourceTracker

_VAL_1234_0 = 1234.0
_VAL_2048_0 = 2048.0
_VAL_40_0 = 40.0
_VAL_55_0 = 55.0


class FakeRedis:
    def __init__(self):
        self.commands = []

    async def zadd(self, key, mapping):
        self.commands.append(("zadd", key, mapping))

    async def expire(self, key, ttl):
        self.commands.append(("expire", key, ttl))

    async def zremrangebyscore(self, key, min_score, max_score):
        self.commands.append(("zrem", key, min_score, max_score))

    async def zrangebyscore(self, key, start, end, withscores=False):
        self.commands.append(("zrange", key, start, end))
        return [f"{start}:{42.0}", "invalid"]


@pytest.mark.asyncio
async def test_record_cpu_usage_success(monkeypatch):
    fake = FakeRedis()
    tracker = ResourceTracker()

    async def provide():
        return fake

    monkeypatch.setattr(tracker, "_get_redis", provide)

    assert await tracker.record_cpu_usage(75.5) is True
    assert any(cmd[0] == "zadd" for cmd in fake.commands)


@pytest.mark.asyncio
async def test_record_cpu_usage_failure(monkeypatch):
    tracker = ResourceTracker()

    async def fail():
        raise RuntimeError("redis down")

    monkeypatch.setattr(tracker, "_get_redis", fail)
    assert await tracker.record_cpu_usage(10.0) is False


@pytest.mark.asyncio
async def test_record_ram_usage_invokes_redis(monkeypatch):
    fake = FakeRedis()
    tracker = ResourceTracker()

    async def provide():
        return fake

    monkeypatch.setattr(tracker, "_get_redis", provide)

    assert await tracker.record_ram_usage(2048.0) is True
    assert any(cmd[0] == "zadd" and "ram" in cmd[1] for cmd in fake.commands)


@pytest.mark.asyncio
async def test_get_cpu_history_parses_entries(monkeypatch):
    fake = FakeRedis()
    tracker = ResourceTracker()

    async def provide():
        return fake

    monkeypatch.setattr(tracker, "_get_redis", provide)

    history = await tracker.get_cpu_history(hours=1)
    assert history and isinstance(history[0][0], int)


@pytest.mark.asyncio
async def test_get_cpu_history_handles_error(monkeypatch):
    tracker = ResourceTracker()

    async def fail():
        raise RuntimeError("redis down")

    monkeypatch.setattr(tracker, "_get_redis", fail)
    assert await tracker.get_cpu_history() == []


@pytest.mark.asyncio
async def test_get_ram_history_and_monitor_loop(monkeypatch):
    fake = FakeRedis()
    tracker = ResourceTracker()

    async def provide():
        return fake

    monkeypatch.setattr(tracker, "_get_redis", provide)

    # RAM history mirrors CPU logic
    history = await tracker.get_ram_history(hours=1)
    assert history and isinstance(history[0][1], float)

    # Exercise monitoring loop
    async def fake_get():
        tracker._stop_monitoring.set()
        return 55.0, 1234.0

    await tracker._monitoring_loop(fake_get)
    assert tracker.get_max_cpu_last_minute() == _VAL_55_0
    assert tracker.get_max_ram_last_minute() == _VAL_1234_0


@pytest.mark.asyncio
async def test_update_current_usage(monkeypatch):
    tracker = ResourceTracker()

    async def record_cpu(value):
        assert value == _VAL_40_0
        return True

    async def record_ram(value):
        assert value == _VAL_2048_0
        return True

    monkeypatch.setattr(tracker, "record_cpu_usage", record_cpu)
    monkeypatch.setattr(tracker, "record_ram_usage", record_ram)

    assert await tracker.update_current_usage(40.0, 2048.0) is True


@pytest.mark.asyncio
async def test_start_and_stop_monitoring(monkeypatch):
    tracker = ResourceTracker()

    loop_calls = []

    async def fake_loop(func):
        loop_calls.append(func)
        tracker._stop_monitoring.set()

    monkeypatch.setattr(tracker, "_monitoring_loop", fake_loop)

    await tracker.start_per_second_monitoring(lambda: None)
    await asyncio.sleep(0)
    assert loop_calls

    await tracker.stop_per_second_monitoring()
