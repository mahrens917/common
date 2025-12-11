from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock

import psutil
import pytest

from common.process_monitor import (
    ProcessInfo,
    ProcessMonitor,
    get_global_process_monitor,
    get_redis_processes,
    get_service_processes,
)

_CONST_13 = 13
_TEST_COUNT_2 = 2
_TEST_COUNT_7 = 7
_VAL_2_0 = 2.0


@pytest.mark.asyncio
async def test_get_service_processes_filters_stale_entries():
    monitor = ProcessMonitor(cache_ttl_seconds=5, scan_interval_seconds=60)
    monitor._last_full_scan = time.time()
    fresh = ProcessInfo(pid=1, name="proc", cmdline=["python"], last_seen=time.time())
    stale = ProcessInfo(pid=2, name="old", cmdline=["python"], last_seen=time.time() - 20)
    monitor._service_cache["kalshi"] = [fresh, stale]

    services = await monitor.get_service_processes("kalshi")

    assert services == [fresh]
    assert monitor._service_cache["kalshi"] == [fresh]


@pytest.mark.asyncio
async def test_get_redis_processes_filters_stale_entries():
    monitor = ProcessMonitor(cache_ttl_seconds=5, scan_interval_seconds=60)
    monitor._last_full_scan = time.time()
    fresh = ProcessInfo(pid=3, name="redis-server", cmdline=["redis"], last_seen=time.time())
    stale = ProcessInfo(pid=4, name="redis-server", cmdline=["redis"], last_seen=time.time() - 20)
    monitor._redis_processes = [fresh, stale]

    redis_processes = await monitor.get_redis_processes()

    assert redis_processes == [fresh]
    assert monitor._redis_processes == [fresh]


def test_matches_service_pattern_and_redis_detection():
    monitor = ProcessMonitor()
    assert monitor.matches_service_pattern(["python", "-m", "src.kalshi"], ["python", "-m", "src.kalshi"])
    assert monitor.matches_service_pattern(["python", "src.kalshi", "-m"], ["python"]) is True
    assert monitor.matches_service_pattern(["python"], ["python", "-m"]) is False

    assert monitor.is_redis_process("redis-server", ["redis"])
    assert monitor.is_redis_process("python", ["manage_redis.py"])
    assert monitor.is_redis_process("python", ["app.py"]) is False


@pytest.mark.asyncio
async def test_get_global_process_monitor_initializes_once(monkeypatch):
    monkeypatch.setattr("common.process_monitor._global_process_monitor", None, raising=False)
    init_mock = AsyncMock()
    monkeypatch.setattr("common.process_monitor.ProcessMonitor.initialize", init_mock, raising=False)

    monitor_one = await get_global_process_monitor()
    monitor_two = await get_global_process_monitor()

    assert monitor_one is monitor_two
    assert init_mock.await_count == 1


@pytest.mark.asyncio
async def test_update_process_metrics_refreshes_timestamp(monkeypatch):
    monitor = ProcessMonitor()
    original_time = time.time() - 50
    monitor._process_cache[42] = ProcessInfo(pid=42, name="proc", cmdline=["python"], last_seen=original_time)

    class FakeProcess:
        def __init__(self, pid):
            self.pid = pid

    monkeypatch.setattr("common.process_monitor_helpers.cache_manager.psutil.Process", FakeProcess)

    updated = await monitor.update_process_metrics(42)
    assert updated is monitor._process_cache[42]
    assert updated.last_seen >= original_time


@pytest.mark.asyncio
async def test_update_process_metrics_removes_missing(monkeypatch):
    monitor = ProcessMonitor()
    monitor._process_cache[13] = ProcessInfo(pid=13, name="gone", cmdline=[], last_seen=time.time())

    def fake_process(pid):
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr("common.process_monitor_helpers.cache_manager.psutil.Process", fake_process)

    result = await monitor.update_process_metrics(_CONST_13)
    assert result is None
    assert _CONST_13 not in monitor._process_cache


@pytest.mark.asyncio
async def test_get_process_by_pid_returns_none_when_stale():
    monitor = ProcessMonitor(cache_ttl_seconds=1)
    monitor._process_cache[_TEST_COUNT_7] = ProcessInfo(pid=_TEST_COUNT_7, name="stale", cmdline=[], last_seen=time.time() - 10)

    result = await monitor.get_process_by_pid(_TEST_COUNT_7)
    assert result is None
    assert _TEST_COUNT_7 not in monitor._process_cache


@pytest.mark.asyncio
async def test_perform_full_scan_populates_caches(monkeypatch):
    monitor = ProcessMonitor()

    class FakeProc:
        def __init__(self, pid, name, cmdline):
            self.info = {"pid": pid, "name": name, "cmdline": cmdline}

    class DeniedProc:
        def __init__(self):
            class DeniedInfo(dict):
                def __getitem__(self, key):
                    raise psutil.AccessDenied(pid=999, name="denied")

            self.info = DeniedInfo()

    processes = [
        FakeProc(1, "python", ["python", "-m", "src.kalshi"]),
        FakeProc(2, "redis-server", ["redis-server", "0.0.0.0:6379"]),
        FakeProc(3, "other", ["other"]),
        DeniedProc(),
    ]

    monkeypatch.setattr("common.process_monitor_helpers.scanner.psutil.process_iter", lambda _attrs: processes)

    await monitor._perform_full_scan()

    assert 1 in monitor._process_cache
    assert monitor._service_cache["kalshi"]
    assert any(proc.pid == _TEST_COUNT_2 for proc in monitor._redis_processes)


@pytest.mark.asyncio
async def test_perform_incremental_scan_triggers_full_scan(monkeypatch):
    monitor = ProcessMonitor()
    # Populate cache with 10 processes
    for pid in range(10):
        monitor._process_cache[pid] = ProcessInfo(pid=pid, name=f"proc{pid}", cmdline=[], last_seen=time.time())

    dead_pids = {0, 1, 2, 3, 4, 5}

    monkeypatch.setattr(
        "common.process_monitor.psutil.pid_exists",
        lambda pid: pid not in dead_pids,
    )

    full_scan_mock = AsyncMock()
    monkeypatch.setattr(
        "common.process_monitor.ProcessMonitor._perform_full_scan",
        full_scan_mock,
        raising=False,
    )

    await monitor._perform_incremental_scan()

    assert full_scan_mock.await_count == 1


@pytest.mark.asyncio
async def test_background_scan_loop_respects_shutdown(monkeypatch):
    monitor = ProcessMonitor(scan_interval_seconds=0.01)
    incremental_mock = AsyncMock()
    monkeypatch.setattr(
        "common.process_monitor.ProcessMonitor._perform_incremental_scan",
        incremental_mock,
        raising=False,
    )

    async def run_loop():
        task = asyncio.create_task(monitor._background_scan_loop())
        await asyncio.sleep(0)
        monitor._shutdown_event.set()
        await task

    await run_loop()
    assert incremental_mock.await_count >= 1


@pytest.mark.asyncio
async def test_incremental_scan_updates_timestamp_without_full_scan(monkeypatch):
    monitor = ProcessMonitor()
    # Populate cache with alive processes
    for pid in range(5):
        monitor._process_cache[pid] = ProcessInfo(pid=pid, name=f"proc{pid}", cmdline=[], last_seen=time.time())

    monkeypatch.setattr("common.process_monitor_helpers.scanner.psutil.pid_exists", lambda pid: True)
    full_scan_mock = AsyncMock()
    monkeypatch.setattr(
        "common.process_monitor.ProcessMonitor._perform_full_scan",
        full_scan_mock,
        raising=False,
    )

    previous_scan_time = monitor._last_full_scan
    await monitor._perform_incremental_scan()

    assert full_scan_mock.await_count == 0
    assert monitor._last_full_scan >= previous_scan_time
    assert monitor._process_cache  # ensure cache untouched


@pytest.mark.asyncio
async def test_background_loop_continues_after_errors(monkeypatch):
    monitor = ProcessMonitor(scan_interval_seconds=0.01)
    call_count = {"count": 0}

    async def flaky_incremental(self):
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise RuntimeError("boom")
        self._shutdown_event.set()

    monkeypatch.setattr(
        "common.process_monitor.ProcessMonitor._perform_incremental_scan",
        flaky_incremental,
        raising=False,
    )

    await monitor._background_scan_loop()
    assert call_count["count"] >= _TEST_COUNT_2


@pytest.mark.asyncio
async def test_initialize_runs_full_scan_once(monkeypatch):
    monitor = ProcessMonitor()
    full_scan_mock = AsyncMock()
    monkeypatch.setattr(
        "common.process_monitor.ProcessMonitor._perform_full_scan",
        full_scan_mock,
        raising=False,
    )

    await monitor.initialize()

    full_scan_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_stop_background_scanning_controls_task(monkeypatch):
    monitor = ProcessMonitor(scan_interval_seconds=0.01)
    monkeypatch.setattr(
        "common.process_monitor.ProcessMonitor.initialize",
        AsyncMock(),
        raising=False,
    )

    async def fake_loop(self):
        await monitor._shutdown_event.wait()

    monkeypatch.setattr(
        "common.process_monitor.ProcessMonitor._background_scan_loop",
        fake_loop,
        raising=False,
    )

    await monitor.start_background_scanning()
    assert monitor._background_task is not None
    assert not monitor._background_task.done()

    await monitor.stop_background_scanning()
    assert monitor._background_task is None


@pytest.mark.asyncio
async def test_stop_background_scanning_handles_timeout(monkeypatch):
    monitor = ProcessMonitor()
    monitor._background_task = asyncio.Future()

    async def fake_wait_for(task, timeout):
        assert task is monitor._background_task
        assert timeout == _VAL_2_0
        raise asyncio.TimeoutError

    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)

    await monitor.stop_background_scanning()

    assert monitor._background_task is None
    assert monitor._shutdown_event.is_set()


@pytest.mark.asyncio
async def test_find_processes_by_keywords_filters(monkeypatch):
    monitor = ProcessMonitor()
    monkeypatch.setattr(monitor, "_ensure_cache_fresh", AsyncMock())
    proc = ProcessInfo(pid=1, name="alpha", cmdline=["/bin/python", "service"], last_seen=time.time())
    monitor._process_cache[1] = proc
    monitor._process_cache[2] = ProcessInfo(pid=2, name="beta", cmdline=["/bin/bash"], last_seen=time.time())

    matches = await monitor.find_processes_by_keywords(["PYTHON", "", "svc"])

    assert matches == [proc]


@pytest.mark.asyncio
async def test_find_processes_by_keywords_returns_empty_when_no_terms(monkeypatch):
    monitor = ProcessMonitor()
    monkeypatch.setattr(monitor, "_ensure_cache_fresh", AsyncMock())

    matches = await monitor.find_processes_by_keywords(["", None])  # type: ignore[list-item]

    assert matches == []


@pytest.mark.asyncio
async def test_perform_full_scan_recovers_from_errors(monkeypatch):
    monitor = ProcessMonitor()

    def broken_iter(_attrs):
        raise RuntimeError("broken iterator")

    monkeypatch.setattr("common.process_monitor_helpers.scanner.psutil.process_iter", broken_iter)

    await monitor._perform_full_scan()

    assert monitor._process_cache == {}


@pytest.mark.asyncio
async def test_perform_incremental_scan_handles_pid_errors(monkeypatch):
    monitor = ProcessMonitor()
    for pid in range(3):
        monitor._process_cache[pid] = ProcessInfo(pid=pid, name=f"proc{pid}", cmdline=[], last_seen=time.time())

    def flaky_pid_exists(pid):
        raise RuntimeError("lookup failed")

    monkeypatch.setattr("common.process_monitor_helpers.scanner.psutil.pid_exists", flaky_pid_exists)
    full_scan_mock = AsyncMock()
    monkeypatch.setattr(
        "common.process_monitor.ProcessMonitor._perform_full_scan",
        full_scan_mock,
        raising=False,
    )

    with pytest.raises(RuntimeError, match="lookup failed"):
        await monitor._perform_incremental_scan()


@pytest.mark.asyncio
async def test_convenience_getters_delegate_to_global_monitor(monkeypatch):
    monitor = AsyncMock()
    monitor.get_service_processes.return_value = [ProcessInfo(pid=1, name="svc", cmdline=[], last_seen=time.time())]
    monitor.get_redis_processes.return_value = [ProcessInfo(pid=2, name="redis", cmdline=[], last_seen=time.time())]

    global_monitor = AsyncMock(return_value=monitor)
    monkeypatch.setattr(
        "common.process_monitor.get_global_process_monitor",
        global_monitor,
        raising=False,
    )

    service_result = await get_service_processes("kalshi")
    redis_result = await get_redis_processes()

    assert service_result == monitor.get_service_processes.return_value
    assert redis_result == monitor.get_redis_processes.return_value
    monitor.get_service_processes.assert_awaited_once_with("kalshi")
    monitor.get_redis_processes.assert_awaited_once()
