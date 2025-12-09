"""Alert logging for memory monitoring."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class AlertLogger:
    """Logs memory monitoring alerts with appropriate severity."""

    def __init__(self, service_name: str):
        """
        Initialize alert logger.

        Args:
            service_name: Name of the service being monitored
        """
        self.service_name = service_name

    def log_alerts(self, analysis: Dict[str, Any]) -> None:
        """Log memory alerts with appropriate severity levels."""
        alerts = analysis.get("alerts")
        if alerts is None:
            alerts = []
        for alert in alerts:
            severity = alert.get("severity")
            if severity is None or severity == "":
                severity = "info"
            message = f"MEMORY_MONITOR[{self.service_name}]: {alert['message']}"

            if severity == "critical":
                logger.error(message)
            elif severity == "error":
                logger.error(message)
            elif severity == "warning":
                logger.warning(message)
            else:
                logger.info(message)
