"""
Redis storage for connection state tracking.

This module provides Redis-based storage for service connection states,
enabling centralized tracking of connection status across all services
for intelligent alert suppression during reconnection events.
"""

import logging
from typing import Any, Dict, List, Optional

from .connection_pool_core import get_redis_pool as _pool_get_redis
from .connection_store_helpers import (
    InitializationManager,
    MetricsManager,
    ReconnectionEventManager,
    StateManager,
)
from .connection_store_helpers.global_instance import get_connection_store
from .connection_store_helpers.state_manager import ConnectionStateInfo
from .typing import RedisClient

logger = logging.getLogger(__name__)

# Export for external use
__all__ = [
    "ConnectionStore",
    "ConnectionStateInfo",
    "get_connection_store",
    "get_redis_pool",
]


get_redis_pool = _pool_get_redis


class ConnectionStore:
    """
    Redis-based storage for connection state information.
    Enables alert suppression during reconnection events.
    """

    def __init__(self) -> None:
        self.redis_client: Optional[RedisClient] = None
        self.connection_states_key = "connection_states"
        self.reconnection_events_key = "reconnection_events"
        self._state_manager: Optional[StateManager] = None
        self._metrics_manager: Optional[MetricsManager] = None
        self._reconnection_event_manager: Optional[ReconnectionEventManager] = None
        self._initialization_manager = InitializationManager(self)
        self.helpers_initialized = False

    async def initialize(self) -> None:
        await self._initialization_manager.ensure_initialized()

    async def get_client(self) -> RedisClient:
        await self.initialize()
        if self.redis_client is None:
            raise ConnectionError("Redis client failed to initialize for ConnectionStore")
        return self.redis_client

    def register_state_manager(self, manager: StateManager) -> None:
        self._state_manager = manager

    def register_metrics_manager(self, manager: MetricsManager) -> None:
        self._metrics_manager = manager

    def register_reconnection_event_manager(self, manager: ReconnectionEventManager) -> None:
        self._reconnection_event_manager = manager

    async def store_connection_state(self, state_info: ConnectionStateInfo) -> bool:
        await self.initialize()
        assert self._state_manager is not None
        return await self._state_manager.store_connection_state(state_info)

    async def store_service_metrics(self, service_name: str, metrics: Dict[str, Any]) -> bool:
        await self.initialize()
        assert self._metrics_manager is not None
        return await self._metrics_manager.store_service_metrics(service_name, metrics)

    async def get_service_metrics(self, service_name: str) -> Optional[Dict[str, Any]]:
        await self.initialize()
        assert self._metrics_manager is not None
        return await self._metrics_manager.get_service_metrics(service_name)

    async def get_connection_state(self, service_name: str) -> Optional[ConnectionStateInfo]:
        await self.initialize()
        assert self._state_manager is not None
        return await self._state_manager.get_connection_state(service_name)

    async def get_all_connection_states(self) -> Dict[str, ConnectionStateInfo]:
        await self.initialize()
        assert self._state_manager is not None
        return await self._state_manager.get_all_connection_states()

    async def is_service_in_reconnection(self, service_name: str) -> bool:
        await self.initialize()
        assert self._state_manager is not None
        return await self._state_manager.is_service_in_reconnection(service_name)

    async def get_services_in_reconnection(self) -> List[str]:
        await self.initialize()
        assert self._state_manager is not None
        return await self._state_manager.get_services_in_reconnection()

    async def record_reconnection_event(self, service_name: str, event_type: str, details: str = "") -> None:
        await self.initialize()
        assert self._reconnection_event_manager is not None
        return await self._reconnection_event_manager.record_reconnection_event(service_name, event_type, details)

    async def get_recent_reconnection_events(self, service_name: str, hours_back: int = 1) -> List[Dict[str, Any]]:
        await self.initialize()
        assert self._reconnection_event_manager is not None
        return await self._reconnection_event_manager.get_recent_reconnection_events(service_name, hours_back)

    async def cleanup_stale_states(self, max_age_hours: int = 24) -> int:
        await self.initialize()
        assert self._state_manager is not None
        return await self._state_manager.cleanup_stale_states(max_age_hours)
