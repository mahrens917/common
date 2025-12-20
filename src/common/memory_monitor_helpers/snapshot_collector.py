"""Snapshot collection for memory monitoring."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List

from .collection_tracker import CollectionTracker
from .metrics_reader import MetricsReader


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time."""

    timestamp: float
    process_memory_mb: float
    system_memory_percent: float
    collection_sizes: Dict[str, int]
    task_count: int


class SnapshotCollector:
    """Collects and stores memory snapshots."""

    def __init__(
        self,
        metrics_reader: MetricsReader,
        collection_tracker: CollectionTracker,
        max_snapshots: int,
    ):
        """
        Initialize snapshot collector.

        Args:
            metrics_reader: Metrics reader for system/process data
            collection_tracker: Collection tracker for collection sizes
            max_snapshots: Maximum number of snapshots to retain
        """
        self.metrics_reader = metrics_reader
        self.collection_tracker = collection_tracker
        self.max_snapshots = max_snapshots
        self.snapshots: List[MemorySnapshot] = []

    def take_snapshot(self) -> MemorySnapshot:
        """Take a snapshot of current memory usage and collection sizes."""
        return self.take_snapshot_with_overrides()

    def take_snapshot_with_overrides(self, *, task_count_supplier=None) -> MemorySnapshot:
        """Take a snapshot allowing overrides for dependent metrics."""
        current_time = time.time()

        # Get memory usage
        process_memory = self.metrics_reader.get_current_memory_usage()
        system_memory = self.metrics_reader.get_system_memory_percent()
        task_count_getter = task_count_supplier or self.metrics_reader.get_current_task_count
        task_count = task_count_getter()

        # Get collection sizes
        collection_sizes = self.collection_tracker.get_collection_sizes()

        snapshot = MemorySnapshot(
            timestamp=current_time,
            process_memory_mb=process_memory,
            system_memory_percent=system_memory,
            collection_sizes=collection_sizes,
            task_count=task_count,
        )

        # Store snapshot
        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots.pop(0)

        return snapshot

    def get_snapshots(self) -> List[MemorySnapshot]:
        """Get all stored snapshots."""
        return self.snapshots

    def get_latest_snapshot(self) -> MemorySnapshot | None:
        """Get the most recent snapshot."""
        if not self.snapshots:
            return None
        return self.snapshots[-1]
