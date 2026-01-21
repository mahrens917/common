"""Applies reset logic to individual fields."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class FieldResetApplicator:
    """Applies local midnight reset logic to specific fields."""

    # Fields that should be cleared (set to None/empty) on reset
    CLEAR_ON_RESET_FIELDS = {"weather_explanation", "last_rule_applied"}

    def __init__(self, reset_evaluator):
        """
        Initialize the field reset applicator.

        Args:
            reset_evaluator: ResetEvaluator instance for determining reset conditions
        """
        self._reset_evaluator = reset_evaluator

    def apply_field_resets(
        self,
        field_name: str,
        current_value: Any,
        previous_data: Dict[str, Any],
        latitude: float,
        longitude: float,
        current_timestamp: Optional[datetime] = None,
    ) -> Tuple[Any, bool]:
        """
        Apply local midnight reset logic to a specific field.

        Args:
            field_name: Name of the field to potentially reset
            current_value: Current value for the field
            previous_data: Previous data to check against
            latitude: Weather station latitude in decimal degrees
            longitude: Weather station longitude in decimal degrees
            current_timestamp: Current timestamp (defaults to now UTC)

        Returns:
            Tuple of (final_value, was_reset)

        Raises:
            ValueError: If coordinates are invalid
        """
        if field_name not in self._reset_evaluator.DAILY_RESET_FIELDS:
            return current_value, False

        should_reset = self._reset_evaluator.should_reset_field(field_name, latitude, longitude, previous_data, current_timestamp)

        if should_reset:
            if field_name in self.CLEAR_ON_RESET_FIELDS:
                # Clear the field (set to None)
                logger.info(f"🔄 MIDNIGHT RESET: Clearing field '{field_name}' to None (new local day)")
                return None, True
            else:
                # Keep current value but mark as reset
                logger.info(f"🔄 MIDNIGHT RESET: Resetting field '{field_name}' to current value {current_value} (new local day)")
                return current_value, True
        # No reset needed, use previous value if available and current is None
        elif field_name in previous_data and current_value is None:
            previous_value = previous_data[field_name]
            logger.debug(f"📋 SAME DAY: Kept previous value for '{field_name}': {previous_value}")
            return previous_value, False
        else:
            logger.debug(f"📋 SAME DAY: Using current value for '{field_name}': {current_value}")
            return current_value, False
