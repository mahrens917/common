"""
Daily Maximum Temperature State Tracking with Confidence-Based Precision

This module implements simplified tracking of daily maximum temperature that
tracks the highest confirmed temperature from any source with confidence metadata
for trading decisions.

Key Features:
- Tracks highest confirmed temperature with precision metadata
- Uses confidence levels (HIGH/MEDIUM) for trading safety margins
- Applies margins in Celsius before CLI conversion to handle non-linearity
- Fail-fast approach with no alternate behavior when data is missing
- Separate tracking of hourly-only maximum for Rule 4 temporal consistency
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .daily_max_state_helpers.config_loader import MetarConfigLoadError
from .daily_max_state_helpers.factory import DailyMaxStateDelegator, DailyMaxStateFactory
from .daily_max_state_helpers.result_generator import DailyMaxResult

logger = logging.getLogger(__name__)

__all__ = [
    "DailyMaxState",
    "DailyMaxResult",
    "MetarConfigLoadError",
    "cli_temp_f",
    "create_daily_max_state",
]


def __getattr__(name: str):
    """Lazy loading for weather-dependent imports."""
    if name == "cli_temp_f":
        from src.weather.temperature_converter import cli_temp_f

        return cli_temp_f
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

_STATE_FIELDS = {
    "max_temp_c": "max_temp_c",
    "precision": "precision",
    "source": "source",
    "timestamp": "timestamp",
    "hourly_max_temp_c": "hourly_max_temp_c",
    "hourly_timestamp": "hourly_timestamp",
}


class DailyMaxState:
    """
    Tracks daily maximum temperature using confidence-based approach.

    Tracks the highest confirmed temperature from any source with precision
    metadata to determine trading confidence levels and safety margins.
    """

    __slots__ = ("_state", "_metar_config", "_delegator")

    def __init__(self):
        self._state = DailyMaxStateFactory.create_initial_state()
        try:
            self._metar_config = self._load_metar_config()
        except MetarConfigLoadError:  # policy_guard: allow-silent-handler
            logger.error("Failed to load METAR data source configuration", exc_info=True)
            raise
        self._delegator = DailyMaxStateDelegator(self._state, self._metar_config)

    def __getattr__(self, item: str):
        if item in _STATE_FIELDS:
            return self._state[_STATE_FIELDS[item]]
        if item == "metar_config":
            return self._metar_config
        raise AttributeError(item)

    def __setattr__(self, key: str, value):
        if key in DailyMaxState.__slots__:
            object.__setattr__(self, key, value)
            return
        if key in _STATE_FIELDS:
            self._state[_STATE_FIELDS[key]] = value
            return
        object.__setattr__(self, key, value)

    def _load_metar_config(self) -> Dict[str, Any]:
        return DailyMaxStateFactory.create_metar_config()

    def add_hourly_observation(self, temp_c: float, timestamp: Optional[datetime] = None) -> None:
        self._delegator.add_hourly_observation(temp_c, timestamp)

    def add_6h_maximum(self, max_c: int, window_end: Optional[datetime] = None) -> None:
        self._delegator.add_6h_maximum(max_c, window_end)

    def get_confidence_level(self) -> str:
        return self._delegator.get_confidence_level()

    def get_safety_margin_c(self) -> float:
        return self._delegator.get_safety_margin_c()

    def get_daily_max_result(self) -> Optional[DailyMaxResult]:
        return self._delegator.get_daily_max_result()

    def get_adjusted_temp_for_rule(self, rule_type: str) -> int:
        return self._delegator.get_adjusted_temp_for_rule(rule_type)

    def get_hourly_only_max_f(self) -> Optional[int]:
        return self._delegator.get_hourly_only_max_f()

    def reset_for_new_day(self) -> None:
        self._delegator.reset_for_new_day()

    def get_state_dict(self) -> Dict[str, Any]:
        return self._delegator.get_state_dict()

    def load_from_state_dict(self, state: Dict[str, Any]) -> None:
        self._delegator.load_from_state_dict(state)


def create_daily_max_state() -> DailyMaxState:
    """
    Factory function to create a new DailyMaxState instance.

    Returns:
        New DailyMaxState instance
    """
    return DailyMaxState()
