"""Growth analysis utilities."""

from typing import Any, Dict, List

from ..snapshot_collector import MemorySnapshot


class GrowthAnalyzer:
    """Analyzes memory and collection growth."""

    def __init__(
        self,
        memory_growth_threshold_mb: float,
        collection_growth_threshold: int,
        check_interval_seconds: int,
    ):
        """Initialize growth analyzer."""
        self.memory_growth_threshold_mb = memory_growth_threshold_mb
        self.collection_growth_threshold = collection_growth_threshold
        self.check_interval_seconds = check_interval_seconds

    def analyze_memory_growth(
        self,
        current: MemorySnapshot,
        previous: MemorySnapshot,
    ) -> List[Dict[str, Any]]:
        """
        Analyze memory growth between snapshots.

        Args:
            current: Current snapshot
            previous: Previous snapshot

        Returns:
            List of alerts for memory growth
        """
        alerts = []
        memory_growth = current.process_memory_mb - previous.process_memory_mb

        if memory_growth > self.memory_growth_threshold_mb:
            alerts.append(
                {
                    "type": "memory_growth",
                    "severity": "warning",
                    "message": (f"Memory grew by {memory_growth:.1f}MB in {self.check_interval_seconds}s"),
                    "current_mb": current.process_memory_mb,
                    "growth_mb": memory_growth,
                }
            )

        return alerts

    def analyze_collection_growth(
        self,
        current: MemorySnapshot,
        previous: MemorySnapshot,
    ) -> List[Dict[str, Any]]:
        """
        Analyze collection size growth.

        Args:
            current: Current snapshot
            previous: Previous snapshot

        Returns:
            List of alerts for collection growth
        """
        alerts = []

        for name, current_size in current.collection_sizes.items():
            if name not in previous.collection_sizes:
                continue

            previous_size = previous.collection_sizes[name]

            if current_size <= 0 or previous_size <= 0:
                continue

            growth = current_size - previous_size
            if growth > self.collection_growth_threshold:
                alerts.append(
                    {
                        "type": "collection_growth",
                        "severity": "error",
                        "message": f"Collection '{name}' grew by {growth} items",
                        "collection": name,
                        "current_size": current_size,
                        "growth": growth,
                    }
                )

        return alerts
