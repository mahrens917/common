"""State management for persistence and reset operations."""

import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state serialization, deserialization, and reset."""

    @staticmethod
    def get_state_dict(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current state as dictionary for serialization.

        Args:
            state: State dictionary to serialize

        Returns:
            Dictionary containing current state
        """
        timestamp = state.get("timestamp")
        hourly_timestamp = state.get("hourly_timestamp")
        max_temp = state.get("max_temp_c")
        hourly_max = state.get("hourly_max_temp_c")
        has_data = max_temp is not None and max_temp != float("-inf")

        return {
            "max_temp_c": max_temp,
            "precision": state.get("precision"),
            "source": state.get("source"),
            "timestamp": timestamp.isoformat() if timestamp else None,
            "has_data": has_data,
            # Include hourly-only tracking
            "hourly_max_temp_c": hourly_max,
            "hourly_timestamp": (hourly_timestamp.isoformat() if hourly_timestamp else None),
        }

    @staticmethod
    def load_from_state_dict(state: Dict[str, Any], state_dict: Dict[str, Any]) -> None:
        """
        Load state from dictionary (for deserialization).

        Args:
            state: State dictionary to update
            state_dict: Dictionary containing state data to load
        """
        state["max_temp_c"] = state_dict.get("max_temp_c", float("-inf"))
        state["precision"] = state_dict.get("precision", None)
        state["source"] = state_dict.get("source", None)

        timestamp_str = state_dict.get("timestamp", None)
        if timestamp_str:
            state["timestamp"] = datetime.fromisoformat(timestamp_str)
        else:
            state["timestamp"] = None

        # Restore hourly-only tracking
        state["hourly_max_temp_c"] = state_dict.get("hourly_max_temp_c", float("-inf"))
        hourly_timestamp_str = state_dict.get("hourly_timestamp", None)
        if hourly_timestamp_str:
            state["hourly_timestamp"] = datetime.fromisoformat(hourly_timestamp_str)
        else:
            state["hourly_timestamp"] = None

        logger.debug(
            f"Loaded state: {state['max_temp_c']}°C ({state['source']}, "
            f"precision={state['precision']}), hourly_max={state['hourly_max_temp_c']}°C"
        )

    @staticmethod
    def reset_for_new_day(state: Dict[str, Any]) -> None:
        """
        Reset state for new local day.

        Args:
            state: State dictionary to reset
        """
        logger.debug("Resetting daily max state for new day")
        state["max_temp_c"] = float("-inf")
        state["precision"] = None
        state["source"] = None
        state["timestamp"] = None
        # Reset hourly-only tracking
        state["hourly_max_temp_c"] = float("-inf")
        state["hourly_timestamp"] = None
