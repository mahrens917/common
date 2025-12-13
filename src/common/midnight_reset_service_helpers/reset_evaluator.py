"""Evaluates whether a specific field should be reset."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ResetEvaluator:
    """Determines if a specific field should be reset based on midnight crossing."""

    # Fields that should reset at local midnight
    DAILY_RESET_FIELDS = {
        "max_temp_f",
        "max_start_time",
        "daily_max_state",  # New bounds-based state tracking
        "t_yes_bid",
        "t_yes_ask",
        "weather_explanation",
        "last_rule_applied",
    }

    def __init__(self, daily_checker, timestamp_mapper):
        """
        Initialize the reset evaluator.

        Args:
            daily_checker: DailyChecker instance for midnight crossing detection
            timestamp_mapper: TimestampMapper instance for field-to-timestamp mapping
        """
        self._daily_checker = daily_checker
        self._timestamp_mapper = timestamp_mapper

    def should_reset_field(
        self,
        field_name: str,
        latitude: float,
        longitude: float,
        previous_data: Dict[str, Any],
        current_timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Check if a specific field should be reset due to local midnight crossing.

        Args:
            field_name: Name of the field to check
            latitude: Weather station latitude in decimal degrees
            longitude: Weather station longitude in decimal degrees
            previous_data: Previous data containing timestamps
            current_timestamp: Current timestamp (defaults to now UTC)

        Returns:
            True if the field should be reset
        """
        if field_name not in self.DAILY_RESET_FIELDS:
            return False

        # Handle empty previous data (first run) - always reset
        if not previous_data:
            logger.info(f"🌅 FIRST RUN: No previous data for field '{field_name}' - treating as new day (reset required)")
            return True

        # Get the relevant timestamp from previous data
        timestamp_field = self._timestamp_mapper.get_timestamp_field_for_reset_field(field_name)
        if timestamp_field not in previous_data:
            logger.info(f"🌅 MISSING TIMESTAMP: No '{timestamp_field}' field for '{field_name}' - treating as new day (reset required)")
            return True

        previous_timestamp_raw = previous_data.get(timestamp_field)
        try:
            previous_timestamp_str = previous_timestamp_raw
            if previous_timestamp_str is None:
                logger.info(
                    f"🌅 NULL TIMESTAMP: Timestamp field '{timestamp_field}' is None for field '{field_name}' - treating as new day (reset required)"
                )
                _none_guard_value = True
                return _none_guard_value

            previous_timestamp = datetime.fromisoformat(previous_timestamp_str.replace("Z", "+00:00"))

            return self._daily_checker.is_new_local_day(latitude, longitude, previous_timestamp, current_timestamp)

        except (  # policy_guard: allow-silent-handler
            ValueError,
            AttributeError,
            KeyError,
        ) as e:
            logger.warning(
                f"⚠️ TIMESTAMP PARSE ERROR: Failed to parse timestamp '{previous_timestamp_raw}' for field '{field_name}': {e} - treating as new day (reset required)"
            )
            return True
