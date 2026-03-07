"""Event and metrics management for connection state tracking."""

import logging
from typing import Any, Dict, List

from ..redis_protocol.connection_store import ConnectionStore
from . import STORE_ERROR_TYPES, build_tracker_error

logger = logging.getLogger(__name__)


class EventManager:
    """Manages connection events, metrics, and cleanup operations."""

    def __init__(self, store: ConnectionStore):
        self.store = store

    async def record_connection_event(self, service_name: str, event_type: str, details: str = "") -> None:
        try:
            await self.store.record_reconnection_event(service_name, event_type, details)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to record connection event for {service_name}", exc)

    async def store_service_metrics(self, service_name: str, metrics: Dict[str, Any]) -> bool:
        try:
            return await self.store.store_service_metrics(service_name, metrics)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to store service metrics for {service_name}", exc)

    async def get_recent_connection_events(self, service_name: str, hours_back: int = 1) -> List[Dict[str, Any]]:
        try:
            return await self.store.get_recent_reconnection_events(service_name, hours_back)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to load connection events for {service_name}", exc)

    async def cleanup_stale_states(self, max_age_hours: int = 24) -> int:
        try:
            return await self.store.cleanup_stale_states(max_age_hours)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error("Failed to cleanup stale connection states", exc)
