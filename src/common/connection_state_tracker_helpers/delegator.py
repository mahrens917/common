"""Delegation helpers for ConnectionStateTracker."""

import asyncio
from json import JSONDecodeError
from typing import Any, Dict, List, Optional

from redis.exceptions import RedisError

from ..connection_state import ConnectionState
from ..redis_protocol.connection_store import ConnectionStateInfo
from .error_builder import build_tracker_error

STORE_ERROR_TYPES = (
    ConnectionError,
    RedisError,
    RuntimeError,
    asyncio.TimeoutError,
    JSONDecodeError,
)


class StateUpdaterDelegator:
    """Delegates state update operations with error handling."""

    def __init__(self, tracker):
        self.tracker = tracker

    async def update_connection_state(
        self,
        service_name: str,
        state: ConnectionState,
        error_context: Optional[str] = None,
        consecutive_failures: int = 0,
    ) -> bool:
        """Update connection state for a service."""
        await self.tracker.initialize()
        try:
            assert self.tracker.state_updater is not None
            return await self.tracker.state_updater.update_connection_state(service_name, state, error_context, consecutive_failures)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to update connection state for {service_name}", exc)


class StateQuerierDelegator:
    """Delegates queries to StateQuerier with error handling."""

    def __init__(self, tracker):
        self.tracker = tracker

    async def get_connection_state(self, service_name: str) -> Optional[ConnectionStateInfo]:
        """Get current connection state for a service."""
        await self.tracker.initialize()
        assert self.tracker.state_querier is not None
        return await self.tracker.state_querier.get_connection_state(service_name)

    async def is_service_in_reconnection(self, service_name: str) -> bool:
        """Check if a service is currently in reconnection mode."""
        await self.tracker.initialize()
        try:
            assert self.tracker.state_querier is not None
            return await self.tracker.state_querier.is_service_in_reconnection(service_name)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to determine reconnection status for {service_name}", exc)

    async def is_service_in_grace_period(self, service_name: str, grace_period_seconds: int = 300) -> bool:
        """Check if a service is within grace period after reconnection."""
        await self.tracker.initialize()
        assert self.tracker.state_querier is not None
        return await self.tracker.state_querier.is_service_in_grace_period(service_name, grace_period_seconds)

    async def get_services_in_reconnection(self) -> List[str]:
        """Get list of all services currently in reconnection mode."""
        await self.tracker.initialize()
        assert self.tracker.state_querier is not None
        try:
            return await self.tracker.state_querier.get_services_in_reconnection()
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error("Failed to list services in reconnection", exc)

    async def get_reconnection_duration(self, service_name: str) -> Optional[float]:
        """Get current reconnection duration for a service."""
        await self.tracker.initialize()
        assert self.tracker.state_querier is not None
        try:
            return await self.tracker.state_querier.get_reconnection_duration(service_name)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to compute reconnection duration for {service_name}", exc)

    async def get_all_connection_states(self) -> Dict[str, ConnectionStateInfo]:
        """Get all current connection states."""
        await self.tracker.initialize()
        assert self.tracker.state_querier is not None
        try:
            return await self.tracker.state_querier.get_all_connection_states()
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error("Failed to load connection states", exc)


class EventManagerDelegator:
    """Delegates event operations to EventManager with error handling."""

    def __init__(self, tracker):
        self.tracker = tracker

    async def record_connection_event(self, service_name: str, event_type: str, details: str = "") -> None:
        """Record a connection-related event for debugging and monitoring."""
        await self.tracker.initialize()
        assert self.tracker.event_manager is not None
        try:
            await self.tracker.event_manager.record_connection_event(service_name, event_type, details)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to record connection event for {service_name}", exc)

    async def store_service_metrics(self, service_name: str, metrics: Dict[str, Any]) -> bool:
        """Persist supplemental service metrics alongside connection state."""
        await self.tracker.initialize()
        assert self.tracker.event_manager is not None
        try:
            return await self.tracker.event_manager.store_service_metrics(service_name, metrics)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to store service metrics for {service_name}", exc)

    async def get_recent_connection_events(self, service_name: str, hours_back: int = 1) -> List[Dict[str, Any]]:
        """Get recent connection events for a service."""
        await self.tracker.initialize()
        assert self.tracker.event_manager is not None
        try:
            return await self.tracker.event_manager.get_recent_connection_events(service_name, hours_back)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to load connection events for {service_name}", exc)

    async def cleanup_stale_states(self, max_age_hours: int = 24) -> int:
        """Clean up stale connection states."""
        await self.tracker.initialize()
        assert self.tracker.event_manager is not None
        try:
            return await self.tracker.event_manager.cleanup_stale_states(max_age_hours)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error("Failed to cleanup stale connection states", exc)
