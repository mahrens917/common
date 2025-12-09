"""Status reporting for connection manager."""

from typing import Any, Dict


class StatusReporter:
    """Reports connection manager status and metrics."""

    def __init__(
        self,
        service_name: str,
        state_manager: Any,
        metrics_tracker: Any,
        config: Any,
    ):
        """Initialize status reporter."""
        self.service_name = service_name
        self.state_manager = state_manager
        self.metrics_tracker = metrics_tracker
        self.config = config

    def get_status(self) -> Dict[str, Any]:
        """Get current connection status and metrics."""
        return {
            "service_name": self.service_name,
            "state": self.state_manager.get_state().value,
            "state_duration": self.state_manager.get_state_duration(),
            "metrics": self.metrics_tracker.get_metrics().__dict__,
            "config": {
                "connection_timeout": self.config.connection_timeout_seconds,
                "max_failures": self.config.max_consecutive_failures,
                "health_check_interval": self.config.health_check_interval_seconds,
            },
        }
