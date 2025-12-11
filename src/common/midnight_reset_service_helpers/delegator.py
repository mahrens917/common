"""Slim delegator for MidnightResetService that coordinates helper modules."""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .max_temp_processor import MaxTempProcessingConfig


class MidnightResetDelegator:
    """Coordinates helper modules for midnight reset logic."""

    # Fields that should reset at local midnight
    DAILY_RESET_FIELDS = {
        "max_temp_f",
        "max_start_time",
        "daily_max_state",
        "t_yes_bid",
        "t_yes_ask",
        "weather_explanation",
        "last_rule_applied",
    }

    # Fields that should be cleared (set to None/empty) on reset
    CLEAR_ON_RESET_FIELDS = {"t_yes_bid", "t_yes_ask", "weather_explanation", "last_rule_applied"}

    def __init__(
        self,
        daily_checker,
        timestamp_mapper,
        reset_evaluator,
        field_reset_applicator,
        max_temp_processor,
    ):
        """Initialize with helper dependencies."""
        self._daily_checker = daily_checker
        self._timestamp_mapper = timestamp_mapper
        self._reset_evaluator = reset_evaluator
        self._field_reset_applicator = field_reset_applicator
        self._max_temp_processor = max_temp_processor

    def is_new_local_day(
        self,
        latitude: float,
        longitude: float,
        previous_timestamp: datetime,
        current_timestamp: Optional[datetime] = None,
    ) -> bool:
        """Check if we've crossed local midnight since the previous timestamp."""
        return self._daily_checker.is_new_local_day(latitude, longitude, previous_timestamp, current_timestamp)

    def should_reset_field(
        self,
        field_name: str,
        latitude: float,
        longitude: float,
        previous_data: Dict[str, Any],
        current_timestamp: Optional[datetime] = None,
    ) -> bool:
        """Check if a specific field should be reset due to local midnight crossing."""
        return self._reset_evaluator.should_reset_field(field_name, latitude, longitude, previous_data, current_timestamp)

    def apply_field_resets(
        self,
        field_name: str,
        current_value: Any,
        previous_data: Dict[str, Any],
        latitude: float,
        longitude: float,
        current_timestamp: Optional[datetime] = None,
    ) -> Tuple[Any, bool]:
        """Apply local midnight reset logic to a specific field."""
        return self._field_reset_applicator.apply_field_resets(
            field_name, current_value, previous_data, latitude, longitude, current_timestamp
        )

    def apply_confidence_based_max_temp_logic(self, config: MaxTempProcessingConfig):
        """Apply confidence-based max_temp_f logic using simplified DailyMaxState."""
        return self._max_temp_processor.apply_confidence_based_max_temp_logic(config)

    def get_timestamp_field_for_reset_field(self, field_name: str) -> str:
        """Get the timestamp field name that should be used to check reset for a given field."""
        return self._timestamp_mapper.get_timestamp_field_for_reset_field(field_name)
