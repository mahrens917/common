from __future__ import annotations

"""Alert throttling helpers."""


from collections import deque
from typing import Deque, Dict

from .models import Alert


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
