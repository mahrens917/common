"""Health alert notification logic."""

import asyncio
import logging

from common.alerter import Alerter, AlertSeverity

logger = logging.getLogger(__name__)

# Local constant for alert failures
ALERT_FAILURE_ERRORS = (ConnectionError, TimeoutError, asyncio.TimeoutError, RuntimeError)


class HealthAlertSender:
    """Sends health alerts via notification system."""

    def __init__(self, service_name: str):
        """
        Initialize alert sender.

        Args:
            service_name: Name of the service
        """
        self.service_name = service_name

    async def send_health_alert(self, message: str, alert_type: str) -> None:
        """Send health alert via notification system."""
        try:
            alerter = Alerter()
            await alerter.send_alert(
                message=f"🔴 {self.service_name.upper()}_WS - Health check failed: {message}",
                severity=AlertSeverity.CRITICAL,
                alert_type=f"{self.service_name}_ws_{alert_type}",
            )
        except ALERT_FAILURE_ERRORS:  # policy_guard: allow-silent-handler
            logger.exception("Failed to send %s health alert", self.service_name)
