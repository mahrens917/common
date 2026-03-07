"""Notification handling for connection manager."""

import logging
from dataclasses import asdict
from typing import Any

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


async def send_connection_notification(manager: Any, is_connected: bool, details: str = "") -> None:
    """Update centralized state tracker with notification."""
    await manager.notification_handler.send_connection_notification(is_connected, details)
    tracker = getattr(manager, "state_tracker", None)
    if tracker is not None and hasattr(tracker, "store_service_metrics"):
        metrics = manager.metrics_tracker.get_metrics()
        if isinstance(metrics, dict):
            metrics_dict = metrics
        else:
            try:
                metrics_dict = asdict(metrics)
            except TypeError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                if hasattr(metrics, "__dict__"):
                    metrics_dict = vars(metrics)
                else:
                    metrics_dict = {}
        await tracker.store_service_metrics(manager.service_name, metrics_dict)
