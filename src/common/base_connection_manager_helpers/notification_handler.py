"""Notification handling for connection manager."""

import logging

from ..connection_state import ConnectionState


class NotificationHandler:
    """Handles connection state notifications."""

    def __init__(self, service_name: str, state_manager, metrics_tracker):
        self.service_name = service_name
        self.state_manager = state_manager
        self.metrics_tracker = metrics_tracker
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def send_connection_notification(self, is_connected: bool, details: str = "") -> None:
        """Update centralized state tracker and log status."""
        new_state = ConnectionState.READY if is_connected else ConnectionState.RECONNECTING
        error_context = None if is_connected else details

        await self.state_manager._broadcast_state_change(new_state, error_context)

        if is_connected:
            metrics = self.metrics_tracker.get_metrics()
            is_startup = metrics.total_connections == 1 and metrics.total_reconnection_attempts <= 1
            if is_startup:
                self.logger.info(f"{self.service_name.upper()} - Started - Connection established")
            else:
                self.logger.info(f"{self.service_name.upper()} - Re-connected after {metrics.consecutive_failures} failures")
        else:
            self.logger.warning(f"{self.service_name.upper()} - Connection lost, attempting reconnection")
