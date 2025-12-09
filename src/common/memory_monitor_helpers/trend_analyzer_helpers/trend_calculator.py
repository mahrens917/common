"""Trend calculation utilities."""

from typing import Any, Dict, List

from ..snapshot_collector import MemorySnapshot

# Constants
_CONST_10 = 10


class TrendCalculator:
    """Calculates memory trends over multiple snapshots."""

    CRITICAL_RATE_MB_PER_MIN = 5.0

    @staticmethod
    def calculate_trends(snapshots: List[MemorySnapshot]) -> List[Dict[str, Any]]:
        """
        Calculate memory trends over recent snapshots.

        Args:
            snapshots: List of memory snapshots

        Returns:
            List of alerts for sustained memory growth
        """
        if len(snapshots) < _CONST_10:
            return []

        recent_snapshots = snapshots[-_CONST_10:]
        memory_trend = (
            recent_snapshots[-1].process_memory_mb - recent_snapshots[0].process_memory_mb
        )
        time_span = recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp

        if time_span <= 0:
            return []

        memory_rate = memory_trend / (time_span / 60)  # MB per minute

        if memory_rate > TrendCalculator.CRITICAL_RATE_MB_PER_MIN:
            return [
                {
                    "type": "memory_leak_trend",
                    "severity": "critical",
                    "message": (
                        f"Sustained memory growth: {memory_rate:.1f}MB/min over {time_span/60:.1f} minutes"
                    ),
                    "rate_mb_per_min": memory_rate,
                    "total_growth_mb": memory_trend,
                }
            ]

        return []
