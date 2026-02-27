"""Health alert notification logic."""

import asyncio
import logging

from common.alerter import Alerter, AlertSeverity
from common.redis_utils import get_redis_connection
from common.service_events import publish_service_event

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
        """Send health alert via notification system and service events stream."""
        try:
            alerter = Alerter()
            alert_message = f"🔴 {self.service_name.upper()}_WS - Health check failed: {message}"
            await alerter.send_alert(
                message=alert_message,
                severity=AlertSeverity.CRITICAL,
                alert_type=f"{self.service_name}_ws_{alert_type}",
            )
            redis = await get_redis_connection()
            await publish_service_event(
                redis,
                service=self.service_name,
                event_type=f"ws_{alert_type}",
                severity="critical",
                message=f"{self.service_name.upper()}_WS: {message}",
            )
        except ALERT_FAILURE_ERRORS:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.exception("Failed to send %s health alert", self.service_name)
