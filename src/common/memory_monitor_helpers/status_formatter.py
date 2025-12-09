"""Status formatting for memory monitoring."""

from typing import Any, Dict

from .collection_tracker import CollectionTracker
from .monitoring_loop import MonitoringLoop
from .snapshot_collector import SnapshotCollector


class StatusFormatter:
    """Formats monitoring status for external consumption."""

    def __init__(
        self,
        service_name: str,
        snapshot_collector: SnapshotCollector,
        collection_tracker: CollectionTracker,
        monitoring_loop: MonitoringLoop,
    ):
        """
        Initialize status formatter.

        Args:
            service_name: Name of the service being monitored
            snapshot_collector: Snapshot collector
            collection_tracker: Collection tracker
            monitoring_loop: Monitoring loop manager
        """
        self.service_name = service_name
        self.snapshot_collector = snapshot_collector
        self.collection_tracker = collection_tracker
        self.monitoring_loop = monitoring_loop

    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        latest = self.snapshot_collector.get_latest_snapshot()
        if latest is None:
            return {"status": "no_data"}

        return {
            "service_name": self.service_name,
            "monitoring_active": self.monitoring_loop.is_monitoring_active(),
            "snapshot_count": len(self.snapshot_collector.get_snapshots()),
            "latest_snapshot": {
                "timestamp": latest.timestamp,
                "process_memory_mb": latest.process_memory_mb,
                "system_memory_percent": latest.system_memory_percent,
                "task_count": latest.task_count,
                "collection_sizes": latest.collection_sizes,
            },
            "tracked_collections": self.collection_tracker.get_tracked_collection_names(),
        }
