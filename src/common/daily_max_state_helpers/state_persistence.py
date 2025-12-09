"""State persistence operations for DailyMaxState."""

from typing import Any, Dict


class StatePersistence:
    """Handles state serialization/deserialization and reset operations."""

    def __init__(self, state: Dict[str, Any]):
        """
        Initialize state persistence helper.

        Args:
            state: State dictionary to manage
        """
        self._state = state

    def reset_for_new_day(self) -> None:
        """Reset state for new local day."""
        from .state_manager import StateManager

        StateManager.reset_for_new_day(self._state)

    def get_state_dict(self) -> Dict[str, Any]:
        """Get current state as dictionary for serialization."""
        from .state_manager import StateManager

        return StateManager.get_state_dict(self._state)

    def load_from_state_dict(self, state_dict: Dict[str, Any]) -> None:
        """Load state from dictionary (for deserialization)."""
        from .state_manager import StateManager

        StateManager.load_from_state_dict(self._state, state_dict)
