"""Health monitoring."""

import logging


class ConnectionHealthMonitor:
    """Monitors connection health."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.health_monitor_failures = 0
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    def reset_failures(self) -> None:
        """Reset failure counter."""
        self.health_monitor_failures = 0

    def increment_failures(self) -> None:
        """Increment failure counter."""
        self.health_monitor_failures += 1

    def get_failure_count(self) -> int:
        """Get failure count."""
        return self.health_monitor_failures

    def should_raise_error(self, max_failures: int) -> bool:
        """Check if should raise error due to too many failures."""
        return self.health_monitor_failures >= max_failures
