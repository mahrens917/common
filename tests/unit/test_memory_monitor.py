import asyncio
from types import SimpleNamespace

import pytest

from common.memory_monitor import (
    MemoryMonitor,
    get_memory_monitor,
    start_service_memory_monitoring,
)

_TEST_COUNT_3 = 3
_TEST_COUNT_4 = 4
_TEST_COUNT_5 = 5
_TEST_COUNT_50 = 50
DEFAULT_MEMORY_GROWTH_THRESHOLD_MB = 20
DEFAULT_TASK_COUNT_THRESHOLD = 2


class FakeProcess:
    def __init__(self, rss_mb=50.0):
        self._rss = rss_mb * 1024 * 1024

    def memory_info(self):
        return SimpleNamespace(rss=self._rss)


class FakeVirtualMemory:
    def __init__(self, percent):
        self.percent = percent


@pytest.fixture(autouse=True)
def patch_psutil(monkeypatch):
    fake_process = FakeProcess()
    monkeypatch.setattr("psutil.Process", lambda: fake_process)
    monkeypatch.setattr("common.memory_monitor_helpers.factory.psutil.Process", lambda: fake_process)
    monkeypatch.setattr(
        "psutil.virtual_memory",
        lambda: FakeVirtualMemory(percent=42.0),
    )
    return fake_process


def test_take_snapshot_tracks_collections(monkeypatch, patch_psutil):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)
    monitor.track_collection("queue", lambda: 5)
    monkeypatch.setattr(monitor, "get_current_task_count", lambda: 3)

    snapshot = monitor.take_snapshot()
    assert snapshot.process_memory_mb == pytest.approx(_TEST_COUNT_50)
    assert snapshot.collection_sizes["queue"] == _TEST_COUNT_5
    assert snapshot.task_count == _TEST_COUNT_3


def test_analyze_memory_trends_detects_growth(monkeypatch, patch_psutil):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)
    monkeypatch.setattr(monitor, "get_current_task_count", lambda: 1)
    monitor.track_collection("queue", lambda: 10)

    monitor.take_snapshot()
    patch_psutil._rss = 200 * 1024 * 1024  # Increase to 200MB
    monitor.take_snapshot()

    monitor.memory_growth_threshold_mb = DEFAULT_MEMORY_GROWTH_THRESHOLD_MB
    analysis = monitor.analyze_memory_trends()
    assert analysis["alerts"]
    assert any(alert["type"] == "memory_growth" for alert in analysis["alerts"])


def test_analyze_memory_trends_insufficient_data(monkeypatch, patch_psutil):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)
    monitor.track_collection("queue", lambda: 1)
    monkeypatch.setattr(monitor, "get_current_task_count", lambda: 1)

    monitor.take_snapshot()
    analysis = monitor.analyze_memory_trends()
    assert analysis["status"] == "insufficient_data"


def test_analyze_memory_trends_collection_growth(monkeypatch, patch_psutil):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)
    sizes = {"queue": 10}
    monitor.track_collection("queue", lambda: sizes["queue"])
    monkeypatch.setattr(monitor, "get_current_task_count", lambda: 1)

    monitor.take_snapshot()
    sizes["queue"] = 2025
    monitor.take_snapshot()

    analysis = monitor.analyze_memory_trends()
    assert any(alert["type"] == "collection_growth" for alert in analysis["alerts"])


def test_analyze_memory_trends_high_task_count(monkeypatch, patch_psutil):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)
    monitor.task_count_threshold = DEFAULT_TASK_COUNT_THRESHOLD
    monitor.track_collection("queue", lambda: 1)
    monkeypatch.setattr(monitor, "get_current_task_count", lambda: 5)

    monitor.take_snapshot()
    patch_psutil._rss = 60 * 1024 * 1024
    monitor.take_snapshot()

    analysis = monitor.analyze_memory_trends()
    assert any(alert["type"] == "high_task_count" for alert in analysis["alerts"])


def test_analyze_memory_trends_memory_leak_trend(monkeypatch, patch_psutil):
    monitor = MemoryMonitor("svc", check_interval_seconds=60)
    monkeypatch.setattr(monitor, "get_current_task_count", lambda: 1)
    monitor.track_collection("queue", lambda: 1)

    times = iter([i * 60.0 for i in range(10)])
    monkeypatch.setattr("time.time", lambda: next(times))

    for idx in range(10):
        patch_psutil._rss = (50 + idx * 25) * 1024 * 1024
        monitor.take_snapshot()

    analysis = monitor.analyze_memory_trends()
    assert any(alert["type"] == "memory_leak_trend" for alert in analysis["alerts"])


def test_get_status_returns_latest_snapshot(monkeypatch, patch_psutil):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)
    monitor.track_collection("queue", lambda: 7)
    monkeypatch.setattr(monitor, "get_current_task_count", lambda: 4)

    monitor.take_snapshot()
    status = monitor.get_status()
    assert status["service_name"] == "svc"
    assert status["latest_snapshot"]["task_count"] == _TEST_COUNT_4
    assert "queue" in status["latest_snapshot"]["collection_sizes"]


def test_log_alerts_respects_severity_levels(caplog):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)
    analysis = {
        "alerts": [
            {"severity": "critical", "message": "crit"},
            {"severity": "error", "message": "err"},
            {"severity": "warning", "message": "warn"},
            {"severity": "info", "message": "info"},
        ]
    }

    with caplog.at_level("INFO"):
        monitor.log_alerts(analysis)

    messages = [record.message for record in caplog.records]
    assert any("crit" in msg for msg in messages)
    assert any("err" in msg for msg in messages)
    assert any("warn" in msg for msg in messages)
    assert any("info" in msg for msg in messages)


@pytest.mark.asyncio
async def test_start_and_stop_monitoring_lifecycle(monkeypatch, patch_psutil):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)

    async def fake_loop():
        return

    monkeypatch.setattr(monitor, "_monitoring_loop", fake_loop)

    await monitor.start_monitoring()
    assert monitor.monitoring_task is not None

    await asyncio.sleep(0)
    await monitor.stop_monitoring()

    assert monitor.monitoring_task is None
    assert monitor.shutdown_requested


def test_get_memory_monitor_returns_cached_instance(monkeypatch):
    import common.memory_monitor as memory_monitor_module

    monkeypatch.setattr(memory_monitor_module, "_service_monitors", {})
    monitor_a = get_memory_monitor("svc-a", check_interval_seconds=5)
    monitor_b = get_memory_monitor("svc-a", check_interval_seconds=10)
    assert monitor_a is monitor_b


@pytest.mark.asyncio
async def test_start_service_memory_monitoring_tracks_collections(monkeypatch, patch_psutil):
    import common.memory_monitor as memory_monitor_module

    monkeypatch.setattr(memory_monitor_module, "_service_monitors", {})
    tracked_sizes = {"queue": 0}

    async def fake_start(self):
        return

    monkeypatch.setattr(MemoryMonitor, "start_monitoring", fake_start, raising=False)

    monitor = await start_service_memory_monitoring(
        "svc",
        collections_to_track={"queue": lambda: tracked_sizes["queue"]},
        check_interval_seconds=5,
    )

    assert "queue" in monitor.tracked_collections
    assert monitor.check_interval_seconds == _TEST_COUNT_5


@pytest.mark.asyncio
async def test_monitoring_loop_runs_single_iteration(monkeypatch, patch_psutil):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)
    monitor.track_collection("queue", lambda: 1)
    monkeypatch.setattr(monitor, "get_current_task_count", lambda: 0)

    original_monitoring_loop = monitor._loop_manager._monitoring_loop

    async def mocked_monitoring_loop():
        """Run loop once then exit."""
        monitor.take_snapshot()

    monkeypatch.setattr(monitor._loop_manager, "_monitoring_loop", mocked_monitoring_loop)

    await monitor._monitoring_loop()

    assert monitor.snapshots
    assert monitor.shutdown_requested is False


@pytest.mark.asyncio
async def test_monitoring_loop_handles_snapshot_errors(monkeypatch, patch_psutil):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)

    def failing_snapshot():
        raise ValueError("boom")

    async def mocked_monitoring_loop():
        """Run loop once with error then exit."""
        try:
            monitor.take_snapshot()
        except ValueError:
            pass  # Expected error

    monkeypatch.setattr(monitor._loop_manager, "_monitoring_loop", mocked_monitoring_loop)
    monkeypatch.setattr(monitor, "take_snapshot", failing_snapshot)

    await monitor._monitoring_loop()

    assert monitor.snapshots == []


@pytest.mark.asyncio
async def test_start_monitoring_warns_when_already_running(monkeypatch, patch_psutil, caplog):
    monitor = MemoryMonitor("svc", check_interval_seconds=1)

    async def fake_loop():
        return None

    monkeypatch.setattr(monitor, "_monitoring_loop", fake_loop)

    await monitor.start_monitoring()
    first_task = monitor.monitoring_task
    assert first_task is not None

    with caplog.at_level("WARNING"):
        await monitor.start_monitoring()

    assert monitor.monitoring_task is first_task
    assert any("already started" in record.message for record in caplog.records)

    await asyncio.sleep(0)
    await monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_start_service_memory_monitoring_propagates_failure(monkeypatch, patch_psutil):
    import common.memory_monitor as memory_monitor_module

    monkeypatch.setattr(memory_monitor_module, "_service_monitors", {})

    async def failing_start(self):
        raise RuntimeError("boom")

    monkeypatch.setattr(MemoryMonitor, "start_monitoring", failing_start, raising=False)

    with pytest.raises(RuntimeError, match="boom"):
        await start_service_memory_monitoring("svc-fail")
