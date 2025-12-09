"""Query operations for connection state information."""

import logging
import time
from typing import Callable, Dict, List, Optional

from ..redis_protocol.connection_store import ConnectionStateInfo, ConnectionStore

logger = logging.getLogger(__name__)


class StateQuerier:
    """Handles queries for connection state information."""

    def __init__(self, store: ConnectionStore, time_provider: Callable[[], float] | None = None):
        self.store = store
        self._time_provider = time_provider or time.time

    async def get_connection_state(self, service_name: str) -> Optional[ConnectionStateInfo]:
        """Get current connection state for a service."""
        return await self.store.get_connection_state(service_name)

    async def is_service_in_reconnection(self, service_name: str) -> bool:
        """Check if a service is currently in reconnection mode."""
        return await self.store.is_service_in_reconnection(service_name)

    async def get_services_in_reconnection(self) -> List[str]:
        """Get list of all services currently in reconnection mode."""
        return await self.store.get_services_in_reconnection()

    async def is_service_in_grace_period(
        self, service_name: str, grace_period_seconds: int = 300
    ) -> bool:
        """Check if a service is within grace period after reconnection."""
        state_info = await self.store.get_connection_state(service_name)

        if not state_info:
            return False

        last_success = state_info.last_successful_connection
        if last_success is not None and self._time_provider() - last_success < grace_period_seconds:
            return True

        if state_info.in_reconnection:
            return True

        return False

    async def get_reconnection_duration(self, service_name: str) -> Optional[float]:
        """Get current reconnection duration for a service."""
        state_info = await self.store.get_connection_state(service_name)

        if (
            not state_info
            or not state_info.in_reconnection
            or state_info.reconnection_start_time is None
        ):
            return None

        return self._time_provider() - state_info.reconnection_start_time

    async def get_all_connection_states(self) -> Dict[str, ConnectionStateInfo]:
        """Get all current connection states."""
        return await self.store.get_all_connection_states()
