"""Validate subscription health."""

import asyncio
import logging
import time
from typing import Dict

from src.common.alerter import Alerter, AlertSeverity

logger = logging.getLogger(__name__)


# Constants
_INTERVAL_SECONDS = 30.0

# Local constant for alert failures
ALERT_FAILURE_ERRORS = (ConnectionError, TimeoutError, asyncio.TimeoutError, RuntimeError)


class SubscriptionHealthError(Exception):
    """Raised when subscription health validation fails."""

    pass


class HealthValidator:
    """Validates subscription health."""

    def __init__(
        self,
        service_name: str,
        websocket_client,
        active_instruments: Dict[str, Dict],
    ):
        """
        Initialize health validator.

        Args:
            service_name: Name of the service
            websocket_client: WebSocket client instance
            active_instruments: Reference to active instruments dict
        """
        self.service_name = service_name
        self.websocket_client = websocket_client
        self.active_instruments = active_instruments
        self._last_health_check = 0.0

    async def validate_health(self) -> None:
        """
        Validate subscription health and fail-fast if unhealthy.

        Raises:
            SubscriptionHealthError: If subscription health validation fails
        """
        current_time = time.time()

        # Skip if checked recently (every 30 seconds)
        if current_time - self._last_health_check < _INTERVAL_SECONDS:
            return

        active_subscription_count = len(self.active_instruments)
        websocket_subscription_count = len(self.websocket_client.active_subscriptions)

        # Fail-fast if no subscriptions are established
        if active_subscription_count == 0 and websocket_subscription_count == 0:
            error_msg = f"CRITICAL: {self.service_name} has no active subscriptions - service in zombie state"
            logger.error(error_msg)

            # Send immediate alert
            await self._send_health_alert(error_msg)

            # Raise exception to trigger reconnection
            raise SubscriptionHealthError(f"{self.service_name}: No active subscriptions")

        logger.debug(
            f"{self.service_name} subscription health check passed: "
            f"{active_subscription_count} active instruments, "
            f"{websocket_subscription_count} websocket subscriptions"
        )

        self._last_health_check = current_time

    async def _send_health_alert(self, error_msg: str) -> None:
        """Send health alert via alerter."""
        try:
            alerter = Alerter()
            await alerter.send_alert(
                message=f"🔴 {self.service_name.upper()}_WS - Subscription health failure: {error_msg}",
                severity=AlertSeverity.CRITICAL,
                alert_type=f"{self.service_name}_ws_subscription_health_failure",
            )
        except ALERT_FAILURE_ERRORS:  # policy_guard: allow-silent-handler
            logger.exception("Failed to send %s subscription health alert", self.service_name)
