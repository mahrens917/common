"""State transition coordination."""

from typing import Any, Optional

from ..connection_state import ConnectionState


class StateTransitionHandler:
    """Handles connection state transitions and metrics updates."""

    def __init__(self, state_manager: Any, metrics_tracker: Any):
        """Initialize state transition handler."""
        self.state_manager = state_manager
        self.metrics_tracker = metrics_tracker

    def transition_state(self, new_state: ConnectionState, error_context: Optional[str] = None) -> None:
        """Transition to a new connection state."""
        self.state_manager.transition_state(new_state, error_context)

        if new_state == ConnectionState.CONNECTED:
            self.metrics_tracker.record_success()
        elif new_state == ConnectionState.FAILED:
            self.metrics_tracker.record_failure()
