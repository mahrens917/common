"""State update logic for connection state tracking."""

import logging
import time
from typing import Callable, Optional

from ..connection_state import ConnectionState
from ..redis_protocol.connection_store import ConnectionStore
from ..redis_protocol.connection_store_helpers.state_manager import ConnectionStateInfo

logger = logging.getLogger(__name__)


class StateUpdater:
    """Handles connection state updates and transitions."""

    def __init__(self, store: ConnectionStore, time_provider: Callable[[], float] | None = None):
        self.store = store
        self._time_provider = time_provider

    async def update_connection_state(
        self,
        service_name: str,
        state: ConnectionState,
        error_context: Optional[str] = None,
        consecutive_failures: int = 0,
    ) -> bool:
        existing_state = await self.store.get_connection_state(service_name)
        current_time = self._time_provider() if self._time_provider else time.time()
        in_reconnection = _is_reconnection_state(state)
        reconnection_start, last_success = _compute_timings(
            existing_state, state, in_reconnection, current_time
        )
        await _record_transition_events(
            self.store, service_name, existing_state, state, in_reconnection, current_time
        )
        state_info = ConnectionStateInfo(
            service_name=service_name,
            state=state,
            timestamp=current_time,
            in_reconnection=in_reconnection,
            reconnection_start_time=reconnection_start,
            error_context=error_context,
            consecutive_failures=consecutive_failures,
            last_successful_connection=last_success,
        )
        success = await self.store.store_connection_state(state_info)
        if success:
            logger.debug(
                "Updated connection state for %s: %s (reconnection: %s)",
                service_name,
                state.value,
                in_reconnection,
            )
        else:
            logger.error("Failed to update connection state for %s", service_name)
        return success


def _is_reconnection_state(state: ConnectionState) -> bool:
    return state in {
        ConnectionState.DISCONNECTED,
        ConnectionState.CONNECTING,
        ConnectionState.RECONNECTING,
        ConnectionState.FAILED,
    }


def _compute_timings(
    existing_state: Optional[ConnectionStateInfo],
    new_state: ConnectionState,
    in_reconnection: bool,
    current_time: float,
) -> tuple[Optional[float], Optional[float]]:
    reconnection_start = None
    last_success = None
    if existing_state:
        reconnection_start = existing_state.reconnection_start_time
        last_success = existing_state.last_successful_connection
        if not existing_state.in_reconnection and in_reconnection:
            reconnection_start = current_time
        elif existing_state.in_reconnection and new_state == ConnectionState.READY:
            reconnection_start = None
            last_success = current_time
    elif in_reconnection:
        reconnection_start = current_time
    elif new_state == ConnectionState.READY:
        last_success = current_time
    return reconnection_start, last_success


async def _record_transition_events(
    store: ConnectionStore,
    service_name: str,
    existing_state: Optional[ConnectionStateInfo],
    new_state: ConnectionState,
    in_reconnection: bool,
    current_time: float,
) -> None:
    if not existing_state:
        return
    if not existing_state.in_reconnection and in_reconnection:
        await store.record_reconnection_event(
            service_name,
            "start",
            f"Entering reconnection from {existing_state.state.value}",
        )
        return
    if existing_state.in_reconnection and new_state == ConnectionState.READY:
        if existing_state.reconnection_start_time is None:
            message = "Reconnection successful"
        else:
            elapsed = current_time - existing_state.reconnection_start_time
            message = f"Reconnection successful after {elapsed:.1f}s"
        await store.record_reconnection_event(service_name, "success", message)
