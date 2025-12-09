"""
Centralized service for handling local midnight field resets.

This service provides consistent local midnight reset logic for weather-related fields
that need to reset at the weather station's local midnight (using standard time, no DST).

Enhanced with bounds-based temperature tracking for accurate max_temp_f calculation.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .midnight_reset_service_helpers import create_midnight_reset_service
from .midnight_reset_service_helpers import daily_checker as _daily_checker_module
from .midnight_reset_service_helpers.max_temp_processor import MaxTempProcessingConfig
from .time_utils import calculate_local_midnight_utc


class MidnightResetService:
    """
    Centralized service for handling local midnight field resets.

    Provides consistent reset logic for weather-related fields that should reset
    at the weather station's local midnight (standard time, no DST).
    """

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

    def __init__(self):
        """Initialize the midnight reset service."""
        self._delegator = create_midnight_reset_service()
        _daily_checker_module.calculate_local_midnight_utc = (
            lambda lat, lon, ts: calculate_local_midnight_utc(lat, lon, ts)
        )

    def is_new_local_day(
        self,
        latitude: float,
        longitude: float,
        previous_timestamp: datetime,
        current_timestamp: Optional[datetime] = None,
    ) -> bool:
        """Check if we've crossed local midnight since the previous timestamp."""
        return self._delegator.is_new_local_day(
            latitude, longitude, previous_timestamp, current_timestamp
        )

    def should_reset_field(
        self,
        field_name: str,
        latitude: float,
        longitude: float,
        previous_data: Dict[str, Any],
        current_timestamp: Optional[datetime] = None,
    ) -> bool:
        """Check if a specific field should be reset due to local midnight crossing."""
        return self._delegator.should_reset_field(
            field_name, latitude, longitude, previous_data, current_timestamp
        )

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
        return self._delegator.apply_field_resets(
            field_name, current_value, previous_data, latitude, longitude, current_timestamp
        )

    def apply_confidence_based_max_temp_logic(
        self,
        current_temp_c: float,
        previous_data: Dict[str, Any],
        latitude: float,
        longitude: float,
        current_timestamp_str: str,
        current_timestamp: Optional[datetime] = None,
        six_hour_max_c: Optional[int] = None,
    ):
        """Apply confidence-based max_temp_f logic using simplified DailyMaxState."""
        should_reset_override = self.should_reset_field(
            "max_temp_f", latitude, longitude, previous_data, current_timestamp
        )
        config = MaxTempProcessingConfig(
            current_temp_c=current_temp_c,
            previous_data=previous_data,
            latitude=latitude,
            longitude=longitude,
            current_timestamp_str=current_timestamp_str,
            current_timestamp=current_timestamp,
            six_hour_max_c=six_hour_max_c,
            should_reset_override=should_reset_override,
        )
        return self._delegator.apply_confidence_based_max_temp_logic(config)

    def get_timestamp_field_for_reset_field(self, field_name: str) -> str:
        """Get the timestamp field name that should be used to check reset for a given field."""
        return self._delegator.get_timestamp_field_for_reset_field(field_name)
