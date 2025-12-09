"""Factory for creating DailyMaxState dependencies."""

from typing import Any, Dict

from .confidence_calculator import ConfidenceCalculator
from .config_loader import ConfigLoader
from .observation_tracker import ObservationTracker
from .result_generator import ResultGenerator
from .state_manager import StateManager


class DailyMaxStateFactory:
    """Factory for creating DailyMaxState dependencies."""

    @staticmethod
    def create_initial_state() -> Dict[str, Any]:
        """
        Create initial state dictionary.

        Returns:
            Dictionary containing initial state
        """
        return {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
            "hourly_max_temp_c": float("-inf"),
            "hourly_timestamp": None,
        }

    @staticmethod
    def create_metar_config() -> Dict[str, Any]:
        """
        Load METAR configuration.

        Returns:
            METAR configuration dictionary

        Raises:
            MetarConfigLoadError: If configuration cannot be loaded
        """
        return ConfigLoader().load_metar_config()


class DailyMaxStateDelegator:
    """Delegates all operations to helper modules."""

    def __init__(self, state: Dict[str, Any], metar_config: Dict[str, Any]):
        """
        Initialize delegator with state and config.

        Args:
            state: State dictionary
            metar_config: METAR configuration
        """
        self._state = state
        self._metar_config = metar_config

    def add_hourly_observation(self, temp_c: float, timestamp=None) -> None:
        """Delegate to ObservationTracker."""
        ObservationTracker.add_hourly_observation(self._state, temp_c, timestamp)

    def add_6h_maximum(self, max_c: int, window_end=None) -> None:
        """Delegate to ObservationTracker."""
        ObservationTracker.add_6h_maximum(self._state, self._metar_config, max_c, window_end)

    def get_confidence_level(self) -> str:
        """Delegate to ConfidenceCalculator."""
        return ConfidenceCalculator.get_confidence_level(self._state.get("precision"))

    def get_safety_margin_c(self) -> float:
        """Delegate to ConfidenceCalculator."""
        return ConfidenceCalculator.get_safety_margin_c(self._state.get("precision"))

    def get_daily_max_result(self):
        """Delegate to ResultGenerator."""
        return ResultGenerator.get_daily_max_result(self._state)

    def get_adjusted_temp_for_rule(self, rule_type: str) -> int:
        """Delegate to ResultGenerator."""
        return ResultGenerator.get_adjusted_temp_for_rule(self._state, rule_type)

    def get_hourly_only_max_f(self):
        """Delegate to ResultGenerator."""
        return ResultGenerator.get_hourly_only_max_f(self._state)

    def reset_for_new_day(self) -> None:
        """Delegate to StateManager."""
        StateManager.reset_for_new_day(self._state)

    def get_state_dict(self) -> Dict[str, Any]:
        """Delegate to StateManager."""
        return StateManager.get_state_dict(self._state)

    def load_from_state_dict(self, state_dict: Dict[str, Any]) -> None:
        """Delegate to StateManager."""
        StateManager.load_from_state_dict(self._state, state_dict)
