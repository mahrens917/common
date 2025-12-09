"""Tracking suppressed alerts and maintaining suppression history."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """
    Types of monitoring alerts that can be suppressed.

    Different alert types have different suppression rules and priorities,
    allowing for fine-grained control over which alerts are suppressed
    during reconnection events.
    """

    ERROR_LOG = "error_log"
    STALE_LOG = "stale_log"
    MESSAGE_METRICS = "message_metrics"
    HEALTH_CHECK = "health_check"
    PROCESS_STATUS = "process_status"
    RECOVERY = "recovery"
    SYSTEM_RESOURCES = "system_resources"
    CONNECTION_ERROR = "connection_error"
    TIMEOUT = "timeout"


@dataclass
class SuppressionDecision:
    """
    Result of alert suppression evaluation.

    Contains the decision and reasoning for whether an alert should be suppressed,
    providing transparency for debugging and monitoring the suppression system.
    """

    should_suppress: bool
    reason: str
    service_name: str
    alert_type: AlertType
    suppression_duration_seconds: Optional[float] = None
    grace_period_remaining_seconds: Optional[float] = None


class SuppressionTracker:
    """Tracks suppression decisions for debugging and monitoring."""

    def __init__(self, max_history_entries: int = 1000):
        """
        Initialize suppression tracker.

        Args:
            max_history_entries: Maximum number of history entries to retain
        """
        self.suppression_history: List[SuppressionDecision] = []
        self.max_history_entries = max_history_entries

    def record_decision(self, decision: SuppressionDecision) -> None:
        """
        Record a suppression decision for debugging and monitoring.

        Args:
            decision: Suppression decision to record
        """
        self.suppression_history.append(decision)

        # Trim history to prevent memory growth
        if len(self.suppression_history) > self.max_history_entries:
            self.suppression_history = self.suppression_history[-self.max_history_entries :]

    def get_recent_decisions(self, limit: int = 50) -> List[SuppressionDecision]:
        """
        Get recent suppression decisions for debugging.

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List of recent suppression decisions
        """
        if not self.suppression_history:
            return []
        return self.suppression_history[-limit:]

    def has_history(self) -> bool:
        """Check if any decisions have been recorded."""
        return len(self.suppression_history) > 0

    def get_all_decisions(self) -> List[SuppressionDecision]:
        """Get all recorded decisions."""
        return self.suppression_history.copy()
