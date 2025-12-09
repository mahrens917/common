import asyncio
from types import SimpleNamespace

import pytest

from src.common.memory_monitor_helpers.collection_tracker import CollectionTracker
from src.common.memory_monitor_helpers.snapshot_collector import MemorySnapshot, SnapshotCollector
from src.common.memory_monitor_helpers.status_formatter import StatusFormatter
from src.common.memory_monitor_helpers.trend_analyzer import TrendAnalyzer


class _FakeMetricsReader:
    def __init__(self, memory_sequence, system_memory=50.0, task_counts=None):
        self._memory_sequence = list(memory_sequence)
        self._system_memory = system_memory
        self._task_counts = task_counts or [0] * len(self._memory_sequence)
        self._index = 0

    def get_current_memory_usage(self) -> float:
        value = self._memory_sequence[self._index]
        return value

    def get_system_memory_percent(self) -> float:
        return self._system_memory

    def get_current_task_count(self) -> int:
        count = self._task_counts[self._index]
        self._index = min(self._index + 1, len(self._memory_sequence) - 1)
        return count


class _FakeMonitoringLoop:
    def __init__(self, active: bool = True):
        self._active = active

    def is_monitoring_active(self) -> bool:
        return self._active


def _make_snapshot(
    timestamp: float,
    memory_mb: float,
    system_memory: float,
    collections,
    task_count: int,
) -> MemorySnapshot:
    return MemorySnapshot(
        timestamp=timestamp,
        process_memory_mb=memory_mb,
        system_memory_percent=system_memory,
        collection_sizes=dict(collections),
        task_count=task_count,
    )


def test_snapshot_collector_stores_bounded_history():
    tracker = CollectionTracker()
    tracker.track_collection("queue", lambda: 3)
    metrics = _FakeMetricsReader([100.0, 120.0], task_counts=[1, 2])
    collector = SnapshotCollector(metrics, tracker, max_snapshots=1)

    first = collector.take_snapshot()
    assert first.process_memory_mb == 100.0
    assert first.collection_sizes["queue"] == 3
    assert collector.get_snapshots() == [first]

    second = collector.take_snapshot()
    assert second.process_memory_mb == 120.0
    assert len(collector.get_snapshots()) == 1
    assert collector.get_latest_snapshot() == second


def test_status_formatter_reports_latest_snapshot():
    tracker = CollectionTracker()
    tracker.track_collection("queue", lambda: 2)
    latest_snapshot = _make_snapshot(10.0, 50.0, 40.0, {"queue": 2}, 5)
    collector = SnapshotCollector(_FakeMetricsReader([0]), tracker, max_snapshots=5)
    collector.snapshots.append(latest_snapshot)
    formatter = StatusFormatter("svc", collector, tracker, _FakeMonitoringLoop(active=False))

    status = formatter.get_status()

    assert status["service_name"] == "svc"
    assert status["monitoring_active"] is False
    assert status["snapshot_count"] == 1
    assert status["latest_snapshot"]["process_memory_mb"] == 50.0
    assert status["tracked_collections"] == ["queue"]


def test_trend_analyzer_detects_growth_and_trends():
    snapshots = []
    # Build 10 snapshots spaced 60s apart with growing memory and collections/task count
    for idx in range(10):
        snapshots.append(
            _make_snapshot(
                timestamp=float(idx * 60),
                memory_mb=float(idx * 12),  # 108MB growth over 9 minutes
                system_memory=55.0,
                collections={"queue": idx * 5},
                task_count=10 if idx == 9 else 1,
            )
        )

    analyzer = TrendAnalyzer(
        memory_growth_threshold_mb=5.0,
        collection_growth_threshold=3,
        task_count_threshold=5,
        check_interval_seconds=60,
    )
    result = analyzer.analyze_memory_trends(snapshots)

    alert_types = {alert["type"] for alert in result["alerts"]}
    assert "memory_growth" in alert_types
    assert "collection_growth" in alert_types
    assert "high_task_count" in alert_types
    assert "memory_leak_trend" in alert_types


@pytest.mark.asyncio
async def test_snapshot_collector_with_task_override():
    tracker = CollectionTracker()
    tracker.track_collection("queue", lambda: 1)
    metrics = _FakeMetricsReader([5.0], task_counts=[0])
    collector = SnapshotCollector(metrics, tracker, max_snapshots=2)

    snapshot = collector.take_snapshot_with_overrides(task_count_supplier=lambda: 42)
    await asyncio.sleep(0)  # exercise asyncio scheduler for coverage

    assert snapshot.task_count == 42
    assert collector.get_latest_snapshot() == snapshot
