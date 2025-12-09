"""Connection metrics tracking."""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConnectionMetrics:
    """Connection metrics for monitoring and alerting."""

    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    consecutive_failures: int = 0
    last_connection_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    current_backoff_delay: float = 0.0
    total_reconnection_attempts: int = 0


class MetricsTracker:
    """Tracks connection metrics."""

    def __init__(self):
        self.metrics = ConnectionMetrics()

    def record_success(self) -> None:
        """Record successful connection."""
        self.metrics.successful_connections += 1
        self.metrics.last_connection_time = time.time()
        self.metrics.consecutive_failures = 0

    def record_failure(self) -> None:
        """Record connection failure."""
        self.metrics.failed_connections += 1
        self.metrics.consecutive_failures += 1
        self.metrics.last_failure_time = time.time()

    def increment_total_connections(self) -> None:
        """Increment total connections counter."""
        self.metrics.total_connections += 1

    def increment_reconnection_attempts(self) -> None:
        """Increment reconnection attempts."""
        self.metrics.total_reconnection_attempts += 1

    def set_backoff_delay(self, delay: float) -> None:
        """Set current backoff delay."""
        self.metrics.current_backoff_delay = delay

    def get_metrics(self) -> ConnectionMetrics:
        """Get current metrics."""
        return self.metrics
