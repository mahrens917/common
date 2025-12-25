"""Notification helpers for connection manager."""

import logging
from dataclasses import asdict
from typing import Any

logger = logging.getLogger(__name__)


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
                # metrics is not a dataclass, convert to dict manually
                if hasattr(metrics, "__dict__"):
                    metrics_dict = vars(metrics)
                else:
                    metrics_dict = {}
        await tracker.store_service_metrics(manager.service_name, metrics_dict)
