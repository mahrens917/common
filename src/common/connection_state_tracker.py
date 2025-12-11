"""Connection state tracker for centralized connection state management."""

import logging
import time as _time
from typing import Any, Dict, List, Optional

from .connection_state import ConnectionState
from .connection_state_tracker_helpers.delegator import (
    EventManagerDelegator,
    StateQuerierDelegator,
    StateUpdaterDelegator,
)
from .connection_state_tracker_helpers.error_builder import (
    ConnectionStateTrackerError,
)
from .connection_state_tracker_helpers.event_manager import EventManager
from .connection_state_tracker_helpers.initializer import TrackerInitializer
from .connection_state_tracker_helpers.state_querier import StateQuerier
from .connection_state_tracker_helpers.state_updater import StateUpdater
from .redis_protocol.connection_store import ConnectionStore, get_connection_store
from .redis_protocol.connection_store_helpers.state_manager import ConnectionStateInfo

logger = logging.getLogger(__name__)
time = _time  # Exposed for test monkeypatching of time.time


class ConnectionStateTracker:
    """High-level interface for connection state tracking."""

    def __init__(self):
        self.connection_store: Optional[ConnectionStore] = None
        self.state_updater: Optional[StateUpdater] = None
        self.state_querier: Optional[StateQuerier] = None
        self.event_manager: Optional[EventManager] = None
        self.time_provider = lambda: time.time()
        self._updater_delegator = StateUpdaterDelegator(self)
        self._state_delegator = StateQuerierDelegator(self)
        self._event_delegator = EventManagerDelegator(self)

    async def initialize(self) -> None:
        """Initialize the connection state tracker with Redis store."""
        if self.connection_store is None:
            # Use module-level accessor to allow tests to override Redis availability.
            self.connection_store = await get_connection_store()
        (
            self.connection_store,
            self.state_updater,
            self.state_querier,
            self.event_manager,
        ) = await TrackerInitializer.initialize_components(
            self.connection_store,
            self.state_updater,
            self.state_querier,
            self.event_manager,
            self.time_provider,
        )

    def _require_store(self) -> None:
        """Raise if the connection store has not been initialized."""
        TrackerInitializer.require_store(self.connection_store)

    async def update_connection_state(
        self,
        service_name: str,
        state: ConnectionState,
        error_context: Optional[str] = None,
        consecutive_failures: int = 0,
    ) -> bool:
        """Update connection state for a service."""
        return await self._updater_delegator.update_connection_state(service_name, state, error_context, consecutive_failures)

    async def get_connection_state(self, service_name: str) -> Optional[ConnectionStateInfo]:
        """Get current connection state for a service."""
        return await self._state_delegator.get_connection_state(service_name)

    async def is_service_in_reconnection(self, service_name: str) -> bool:
        """Check if a service is currently in reconnection mode."""
        return await self._state_delegator.is_service_in_reconnection(service_name)

    async def get_services_in_reconnection(self) -> List[str]:
        """Get list of all services currently in reconnection mode."""
        return await self._state_delegator.get_services_in_reconnection()

    async def is_service_in_grace_period(self, service_name: str, grace_period_seconds: int = 300) -> bool:
        """Check if a service is within grace period after reconnection."""
        return await self._state_delegator.is_service_in_grace_period(service_name, grace_period_seconds)

    async def get_reconnection_duration(self, service_name: str) -> Optional[float]:
        """Get current reconnection duration for a service."""
        return await self._state_delegator.get_reconnection_duration(service_name)

    async def get_all_connection_states(self) -> Dict[str, ConnectionStateInfo]:
        """Get all current connection states."""
        return await self._state_delegator.get_all_connection_states()

    async def record_connection_event(self, service_name: str, event_type: str, details: str = "") -> None:
        """Record a connection-related event for debugging and monitoring."""
        await self._event_delegator.record_connection_event(service_name, event_type, details)

    async def store_service_metrics(self, service_name: str, metrics: Dict[str, Any]) -> bool:
        """Persist supplemental service metrics alongside connection state."""
        return await self._event_delegator.store_service_metrics(service_name, metrics)

    async def get_recent_connection_events(self, service_name: str, hours_back: int = 1) -> List[Dict[str, Any]]:
        """Get recent connection events for a service."""
        return await self._event_delegator.get_recent_connection_events(service_name, hours_back)

    async def cleanup_stale_states(self, max_age_hours: int = 24) -> int:
        """Clean up stale connection states."""
        return await self._event_delegator.cleanup_stale_states(max_age_hours)


_connection_state_tracker: Optional[ConnectionStateTracker] = None


async def get_connection_state_tracker() -> ConnectionStateTracker:
    """Get the global connection state tracker instance."""
    global _connection_state_tracker
    if _connection_state_tracker is None:
        _connection_state_tracker = ConnectionStateTracker()
        await _connection_state_tracker.initialize()
    return _connection_state_tracker


__all__ = ["ConnectionStateTracker", "ConnectionStateTrackerError", "get_connection_state_tracker"]
