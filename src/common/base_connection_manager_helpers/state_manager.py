"""Connection state management."""

import logging
import time
from typing import Optional

from ..async_helpers import safely_schedule_coroutine
from ..connection_state import ConnectionState
from ..connection_state_tracker import ConnectionStateTracker, get_connection_state_tracker


class ConnectionStateManager:
    """Manages connection state transitions and broadcasting."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.state = ConnectionState.DISCONNECTED
        self.state_change_time = time.time()
        self.state_tracker: Optional[ConnectionStateTracker] = None
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    def transition_state(self, new_state: ConnectionState, error_context: Optional[str] = None) -> None:
        """Transition to a new connection state."""
        if self.state != new_state:
            previous_state = self.state
            self.state = new_state
            self.state_change_time = time.time()
            self.logger.info(f"State transition: {previous_state.value} -> {new_state.value}")
            broadcast_factory = lambda: self._broadcast_state_change(new_state, error_context)
            safely_schedule_coroutine(broadcast_factory)

    async def _initialize_state_tracker(self) -> None:
        """Initialize the connection state tracker."""
        if self.state_tracker is None:
            self.state_tracker = await get_connection_state_tracker()
            self.logger.debug("Connection state tracker initialized")

    async def _broadcast_state_change(self, new_state: ConnectionState, error_context: Optional[str] = None) -> None:
        """Broadcast connection state change."""
        if self.state_tracker is None:
            await self._initialize_state_tracker()

        if self.state_tracker:
            await self.state_tracker.update_connection_state(
                service_name=self.service_name,
                state=new_state,
                error_context=error_context,
                consecutive_failures=0,
            )

    def get_state(self) -> ConnectionState:
        """Get current state."""
        return self.state

    def get_state_duration(self) -> float:
        """Get time in current state."""
        return time.time() - self.state_change_time
