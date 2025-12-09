"""Trend analysis for memory monitoring."""

from typing import Any, Dict, List

from .snapshot_collector import MemorySnapshot

# Constants
_CONST_2 = 2


class TrendAnalyzer:
    """Analyzes memory trends to detect potential leaks."""

    def __init__(
        self,
        memory_growth_threshold_mb: float,
        collection_growth_threshold: int,
        task_count_threshold: int,
        check_interval_seconds: int,
    ):
        """
        Initialize trend analyzer.

        Args:
            memory_growth_threshold_mb: Alert threshold for memory growth
            collection_growth_threshold: Alert threshold for collection growth
            task_count_threshold: Alert threshold for task count
            check_interval_seconds: Time between checks
        """
        self.memory_growth_threshold_mb = memory_growth_threshold_mb
        self.collection_growth_threshold = collection_growth_threshold
        self.task_count_threshold = task_count_threshold
        self.check_interval_seconds = check_interval_seconds

    def analyze_memory_trends(self, snapshots: List[MemorySnapshot]) -> Dict[str, Any]:
        """
        Analyze memory usage trends to detect potential leaks.

        Args:
            snapshots: List of memory snapshots to analyze

        Returns:
            Dictionary with analysis results and alerts
        """
        from .trend_analyzer_helpers import AlertBuilder, GrowthAnalyzer, TrendCalculator

        if len(snapshots) < _CONST_2:
            return {"status": "insufficient_data", "alerts": []}

        current = snapshots[-1]
        previous = snapshots[-2]

        # Create analyzers
        growth_analyzer = GrowthAnalyzer(
            self.memory_growth_threshold_mb,
            self.collection_growth_threshold,
            self.check_interval_seconds,
        )
        alert_builder = AlertBuilder(self.task_count_threshold)

        # Collect all alerts
        alerts = []
        alerts.extend(growth_analyzer.analyze_memory_growth(current, previous))
        alerts.extend(growth_analyzer.analyze_collection_growth(current, previous))
        alerts.extend(alert_builder.build_task_count_alert(current))
        alerts.extend(TrendCalculator.calculate_trends(snapshots))

        return {
            "status": "analyzed",
            "current_memory_mb": current.process_memory_mb,
            "system_memory_percent": current.system_memory_percent,
            "task_count": current.task_count,
            "collection_sizes": current.collection_sizes,
            "alerts": alerts,
        }
