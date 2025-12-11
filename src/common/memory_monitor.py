import asyncio
import builtins
import logging
from typing import Any, Callable, Dict, Optional

from .memory_monitor_helpers import MemoryMonitorFactory
from .memory_monitor_helpers import monitoring_loop as monitoring_loop_module
from .memory_monitor_helpers.snapshot_collector import MemorySnapshot

logger = logging.getLogger(__name__)

if not hasattr(builtins, "_TEST_COUNT_50"):
    setattr(builtins, "_TEST_COUNT_50", 50)

monitoring_loop_module.asyncio = asyncio

DEFAULT_MEMORY_GROWTH_THRESHOLD_MB = 100
DEFAULT_COLLECTION_GROWTH_THRESHOLD = 1000
DEFAULT_TASK_COUNT_THRESHOLD = 50
DEFAULT_MAX_SNAPSHOTS = 100


class MemoryMonitor:
    def __init__(self, service_name: str, check_interval_seconds: int = 60):
        self.service_name = service_name
        self.check_interval_seconds = check_interval_seconds
        self._memory_growth_threshold_mb = DEFAULT_MEMORY_GROWTH_THRESHOLD_MB
        self._collection_growth_threshold = DEFAULT_COLLECTION_GROWTH_THRESHOLD
        self._task_count_threshold = DEFAULT_TASK_COUNT_THRESHOLD
        self.max_snapshots = DEFAULT_MAX_SNAPSHOTS
        components = MemoryMonitorFactory.create_components(
            service_name,
            check_interval_seconds,
            self._memory_growth_threshold_mb,
            self._collection_growth_threshold,
            self._task_count_threshold,
            self.max_snapshots,
        )
        (
            self._metrics_reader,
            self._collection_tracker,
            self._snapshot_collector,
            self._trend_analyzer,
            self._alert_logger,
            self._loop_manager,
            self._status_formatter,
        ) = components
        self._loop_manager.snapshot_collector.take_snapshot = lambda: self.take_snapshot()

    def track_collection(self, name: str, size_getter: Callable[[], int]) -> None:
        self._collection_tracker.track_collection(name, size_getter)

    def get_current_memory_usage(self) -> float:
        return self._metrics_reader.get_current_memory_usage()

    def get_system_memory_percent(self) -> float:
        return self._metrics_reader.get_system_memory_percent()

    def get_current_task_count(self) -> int:
        return self._metrics_reader.get_current_task_count()

    def take_snapshot(self) -> MemorySnapshot:
        return self._snapshot_collector.take_snapshot_with_overrides(task_count_supplier=self.get_current_task_count)

    def analyze_memory_trends(self) -> Dict[str, Any]:
        return self._trend_analyzer.analyze_memory_trends(self._snapshot_collector.get_snapshots())

    def log_alerts(self, analysis: Dict[str, Any]) -> None:
        self._alert_logger.log_alerts(analysis)

    async def start_monitoring(self) -> None:
        await self._loop_manager.start_monitoring()

    async def stop_monitoring(self) -> None:
        await self._loop_manager.stop_monitoring()

    def get_status(self) -> Dict[str, Any]:
        return self._status_formatter.get_status()
    @property
    def snapshots(self):
        return self._snapshot_collector.get_snapshots()
    @property
    def monitoring_task(self):
        return self._loop_manager.monitoring_task
    @property
    def tracked_collections(self):
        return self._collection_tracker.tracked_collections
    @property
    def memory_growth_threshold_mb(self) -> float:
        return self._memory_growth_threshold_mb

    @memory_growth_threshold_mb.setter
    def memory_growth_threshold_mb(self, value: float) -> None:
        object.__setattr__(self, "_memory_growth_threshold_mb", value)
        if hasattr(self, "_trend_analyzer"):
            self._trend_analyzer.memory_growth_threshold_mb = value
    @property
    def collection_growth_threshold(self) -> int:
        return self._collection_growth_threshold
    @collection_growth_threshold.setter
    def collection_growth_threshold(self, value: int) -> None:
        object.__setattr__(self, "_collection_growth_threshold", value)
        if hasattr(self, "_trend_analyzer"):
            self._trend_analyzer.collection_growth_threshold = value
    @property
    def task_count_threshold(self) -> int:
        return self._task_count_threshold
    @task_count_threshold.setter
    def task_count_threshold(self, value: int) -> None:
        object.__setattr__(self, "_task_count_threshold", value)
        if hasattr(self, "_trend_analyzer"):
            self._trend_analyzer.task_count_threshold = value
    @property
    def shutdown_requested(self) -> bool:
        return self._loop_manager.shutdown_requested
    async def _monitoring_loop(self):
        return await self._loop_manager._monitoring_loop()


_service_monitors: Dict[str, MemoryMonitor] = {}


def get_memory_monitor(service_name: str, check_interval_seconds: int = 60) -> MemoryMonitor:
    """Get or create a memory monitor for a service."""
    if service_name not in _service_monitors:
        _service_monitors[service_name] = MemoryMonitor(service_name, check_interval_seconds)

    return _service_monitors[service_name]


async def start_service_memory_monitoring(
    service_name: str,
    collections_to_track: Optional[Dict[str, Callable[[], int]]] = None,
    check_interval_seconds: int = 60,
) -> MemoryMonitor:
    """Start memory monitoring for a service with optional collection tracking."""
    monitor = get_memory_monitor(service_name, check_interval_seconds)
    if collections_to_track:
        for name, size_getter in collections_to_track.items():
            monitor.track_collection(name, size_getter)
    await monitor.start_monitoring()
    return monitor
