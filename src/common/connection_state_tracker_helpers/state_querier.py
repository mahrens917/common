"""Query operations for connection state information."""

from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional

from ..redis_protocol.connection_store import ConnectionStateInfo, ConnectionStore
from . import STORE_ERROR_TYPES, build_tracker_error

logger = logging.getLogger(__name__)


class StateQuerier:
    """Handles queries for connection state information."""

    def __init__(self, store: ConnectionStore, time_provider: Callable[[], float] | None = None):
        self.store = store
        self._time_provider = time_provider or time.time

    async def get_connection_state(self, service_name: str) -> Optional[ConnectionStateInfo]:
        return await self.store.get_connection_state(service_name)

    async def is_service_in_reconnection(self, service_name: str) -> bool:
        try:
            return await self.store.is_service_in_reconnection(service_name)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to determine reconnection status for {service_name}", exc)

    async def get_services_in_reconnection(self) -> List[str]:
        try:
            return await self.store.get_services_in_reconnection()
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error("Failed to list services in reconnection", exc)

    async def is_service_in_grace_period(self, service_name: str, grace_period_seconds: int = 300) -> bool:
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
        try:
            return await self._compute_reconnection_duration(service_name)
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error(f"Failed to compute reconnection duration for {service_name}", exc)

    async def _compute_reconnection_duration(self, service_name: str) -> Optional[float]:
        state_info = await self.store.get_connection_state(service_name)

        if not state_info or not state_info.in_reconnection or state_info.reconnection_start_time is None:
            return None

        return self._time_provider() - state_info.reconnection_start_time

    async def get_all_connection_states(self) -> Dict[str, ConnectionStateInfo]:
        try:
            return await self.store.get_all_connection_states()
        except STORE_ERROR_TYPES as exc:
            raise build_tracker_error("Failed to load connection states", exc)
