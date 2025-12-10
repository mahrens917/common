import asyncio
from unittest.mock import AsyncMock

import pytest

from common.cpu_monitor import CpuMonitor


@pytest.mark.asyncio
async def test_initialize_caches_first_reading():
    monitor = CpuMonitor()
    monitor._read_cpu_percent = AsyncMock(return_value=37.5)  # type: ignore[assignment]

    await monitor.initialize()

    assert monitor._initialized is True
    cached_value = await monitor.get_cpu_percent()
    assert cached_value == pytest.approx(37.5)
    assert monitor._read_cpu_percent.await_count == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_start_background_updates_requires_initialize():
    monitor = CpuMonitor()

    with pytest.raises(RuntimeError):
        await monitor.start_background_updates()


@pytest.mark.asyncio
async def test_background_updates_refresh_value():
    monitor = CpuMonitor()
    call_log = []

    async def fake_read():
        idx = len(call_log)
        if idx == 0:
            call_log.append("init")
            return 10.0

        call_log.append("update")
        monitor._running = False
        return 42.0

    monitor._read_cpu_percent = fake_read  # type: ignore[assignment]

    await monitor.initialize()
    await monitor.start_background_updates()

    assert monitor._task is not None
    await asyncio.wait_for(monitor._task, timeout=1.0)

    await monitor.stop_background_updates()

    assert monitor._current_cpu_percent == pytest.approx(42.0)
    assert call_log == ["init", "update"]


@pytest.mark.asyncio
async def test_get_cpu_percent_refreshes_when_cache_missing():
    monitor = CpuMonitor()
    monitor._initialized = True
    monitor._current_cpu_percent = None
    monitor._read_cpu_percent = AsyncMock(return_value=65.0)  # type: ignore[assignment]

    value = await monitor.get_cpu_percent()

    assert value == pytest.approx(65.0)
    assert monitor._current_cpu_percent == pytest.approx(65.0)
    assert monitor._read_cpu_percent.await_count == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_initialize_idempotent():
    monitor = CpuMonitor()
    monitor._read_cpu_percent = AsyncMock(return_value=12.0)  # type: ignore[assignment]

    await monitor.initialize()
    monitor._read_cpu_percent.reset_mock()

    await monitor.initialize()
    monitor._read_cpu_percent.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_background_updates_no_duplicate_tasks(monkeypatch):
    monitor = CpuMonitor()
    monitor._initialized = True
    loop = asyncio.get_running_loop()
    monitor._task = loop.create_future()

    def fail_create_task(*args, **kwargs):
        raise AssertionError("create_task should not be called when task is active")

    monkeypatch.setattr(asyncio, "create_task", fail_create_task)

    await monitor.start_background_updates()

    assert monitor._task is not None
    assert not monitor._task.done()
