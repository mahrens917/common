"""Event and metrics management for connection state tracking."""

import logging
from typing import Any, Dict, List

from ..redis_protocol.connection_store import ConnectionStore

logger = logging.getLogger(__name__)


class EventManager:
    """Manages connection events, metrics, and cleanup operations."""

    def __init__(self, store: ConnectionStore):
        self.store = store

    async def record_connection_event(self, service_name: str, event_type: str, details: str = "") -> None:
        """Record a connection-related event for debugging and monitoring."""
        await self.store.record_reconnection_event(service_name, event_type, details)

    async def store_service_metrics(self, service_name: str, metrics: Dict[str, Any]) -> bool:
        """Persist supplemental service metrics alongside connection state."""
        return await self.store.store_service_metrics(service_name, metrics)

    async def get_recent_connection_events(self, service_name: str, hours_back: int = 1) -> List[Dict[str, Any]]:
        """Get recent connection events for a service."""
        return await self.store.get_recent_reconnection_events(service_name, hours_back)

    async def cleanup_stale_states(self, max_age_hours: int = 24) -> int:
        """Clean up stale connection states."""
        return await self.store.cleanup_stale_states(max_age_hours)
