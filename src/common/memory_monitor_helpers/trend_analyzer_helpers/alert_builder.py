"""Alert building utilities."""

from typing import Any, Dict, List

from ..snapshot_collector import MemorySnapshot


class AlertBuilder:
    """Builds alerts for high task counts."""

    def __init__(self, task_count_threshold: int):
        """Initialize alert builder."""
        self.task_count_threshold = task_count_threshold

    def build_task_count_alert(self, current: MemorySnapshot) -> List[Dict[str, Any]]:
        """
        Build alert for high task count.

        Args:
            current: Current snapshot

        Returns:
            List containing alert if threshold exceeded
        """
        if current.task_count > self.task_count_threshold:
            return [
                {
                    "type": "high_task_count",
                    "severity": "warning",
                    "message": f"High task count: {current.task_count} active tasks",
                    "task_count": current.task_count,
                }
            ]

        return []
