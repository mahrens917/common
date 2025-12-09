"""
Connection health monitor with fail-fast validation - slim coordinator.

Monitors both WebSocket connection status and data flow to prevent zombie
connection states where the connection appears healthy but no data flows.
"""

import logging
import time

from .connection_health_monitor_helpers import HealthAlertSender, HealthChecker, MonitorLifecycle
from .interfaces import SubscriptionAwareWebSocketClient

logger = logging.getLogger(__name__)


class ConnectionHealthMonitor:
    """
    Monitors WebSocket connection health with fail-fast validation.

    Slim coordinator delegating to specialized helper modules.
    """

    def __init__(
        self,
        service_name: str,
        websocket_client: SubscriptionAwareWebSocketClient,
        subscription_manager,
        stats_collector,
        health_check_interval_seconds: int = 30,
        max_silent_duration_seconds: int = 300,
    ):
        """
        Initialize connection health monitor.

        Args:
            service_name: Name of the service (e.g., 'deribit', 'kalshi')
            websocket_client: WebSocket client instance
            subscription_manager: Subscription manager instance
            stats_collector: Statistics collector instance
            health_check_interval_seconds: Interval between health checks
            max_silent_duration_seconds: Max seconds without data before failure
        """
        self.service_name = service_name
        self.websocket_client = websocket_client
        self.subscription_manager = subscription_manager
        self.stats_collector = stats_collector
        self.health_check_interval_seconds = health_check_interval_seconds
        self.max_silent_duration_seconds = max_silent_duration_seconds
        self._last_health_check = 0.0

        # Initialize helper modules
        self._health_checker = HealthChecker(
            service_name,
            websocket_client,
            subscription_manager,
            stats_collector,
            max_silent_duration_seconds,
        )
        self._alert_sender = HealthAlertSender(service_name)
        self._lifecycle = MonitorLifecycle(service_name, health_check_interval_seconds)

    async def start_monitoring(self) -> None:
        await self._lifecycle.start_monitoring(self.check_health)

    async def stop_monitoring(self) -> None:
        await self._lifecycle.stop_monitoring()

    async def check_health(self) -> None:
        current_time = time.time()
        if current_time - self._last_health_check < self.health_check_interval_seconds:
            return

        logger.debug("Performing %s health check", self.service_name)

        try:
            self._health_checker.check_connection_status()
        except ConnectionError as exc:
            await self._alert_sender.send_health_alert(str(exc), "connection_down")
            raise

        try:
            self._health_checker.check_subscription_status()
        except ConnectionError as exc:
            await self._alert_sender.send_health_alert(str(exc), "no_subscriptions")
            raise

        try:
            time_since_data = self._health_checker.check_data_flow(current_time)
        except ConnectionError as exc:
            await self._alert_sender.send_health_alert(str(exc), "no_data_flow")
            raise

        self._health_checker.log_health_check_passed(time_since_data)
        self._last_health_check = current_time

    def is_healthy(self) -> bool:
        return self._health_checker.is_healthy_sync()
