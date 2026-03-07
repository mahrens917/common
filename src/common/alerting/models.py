from __future__ import annotations

"""Shared data structures and throttling for monitor alerting."""

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Deque, Dict, Optional


class AlerterError(RuntimeError):
    """Base exception for alerting failures."""


class AlertSeverity(Enum):
    """Simple alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Simple alert data structure."""

    message: str
    severity: AlertSeverity
    timestamp: float
    alert_type: str
    details: Optional[Dict[str, Any]] = None


class AlertThrottle:
    """Sliding-window throttle that caps alert volume."""

    def __init__(self, window_seconds: float, max_alerts: int) -> None:
        self._window_seconds = window_seconds
        self._max_alerts = max_alerts
        self._recent: Dict[str, Deque[float]] = {}

    def record(self, alert: Alert) -> bool:
        """Record an alert and return True when it should be dispatched."""

        now = alert.timestamp
        queue = self._recent.setdefault(alert.alert_type, deque())
        self._prune(queue, now)
        if len(queue) >= self._max_alerts:
            return False
        queue.append(now)
        return True

    def _prune(self, queue: Deque[float], now: float) -> None:
        """Remove alerts that fall outside the sliding window."""

        window_start = now - self._window_seconds
        while queue and queue[0] < window_start:
            queue.popleft()
