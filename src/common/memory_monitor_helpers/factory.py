"""Factory for creating MemoryMonitor components."""

import psutil

from .alert_logger import AlertLogger
from .collection_tracker import CollectionTracker
from .metrics_reader import MetricsReader
from .monitoring_loop import MonitoringLoop
from .snapshot_collector import SnapshotCollector
from .status_formatter import StatusFormatter
from .trend_analyzer import TrendAnalyzer


class MemoryMonitorFactory:
    """Factory for creating and wiring MemoryMonitor components."""

    @staticmethod
    def create_components(
        service_name: str,
        check_interval_seconds: int,
        memory_growth_threshold_mb: float,
        collection_growth_threshold: int,
        task_count_threshold: int,
        max_snapshots: int,
    ) -> tuple:
        """
        Create all components needed for memory monitoring.

        Args:
            service_name: Name of the service being monitored
            check_interval_seconds: Time between checks
            memory_growth_threshold_mb: Alert threshold for memory growth
            collection_growth_threshold: Alert threshold for collection growth
            task_count_threshold: Alert threshold for task count
            max_snapshots: Maximum number of snapshots to retain

        Returns:
            Tuple of (metrics_reader, collection_tracker, snapshot_collector,
                     trend_analyzer, alert_logger, monitoring_loop, status_formatter)
        """
        # Create process handle
        process = psutil.Process()

        # Create core components
        metrics_reader = MetricsReader(process)
        collection_tracker = CollectionTracker()

        # Create snapshot collector
        snapshot_collector = SnapshotCollector(metrics_reader, collection_tracker, max_snapshots)

        # Create trend analyzer
        trend_analyzer = TrendAnalyzer(
            memory_growth_threshold_mb,
            collection_growth_threshold,
            task_count_threshold,
            check_interval_seconds,
        )

        # Create alert logger
        alert_logger = AlertLogger(service_name)

        # Create monitoring loop
        monitoring_loop = MonitoringLoop(snapshot_collector, trend_analyzer, alert_logger, check_interval_seconds)

        # Create status formatter
        status_formatter = StatusFormatter(service_name, snapshot_collector, collection_tracker, monitoring_loop)

        return (
            metrics_reader,
            collection_tracker,
            snapshot_collector,
            trend_analyzer,
            alert_logger,
            monitoring_loop,
            status_formatter,
        )
