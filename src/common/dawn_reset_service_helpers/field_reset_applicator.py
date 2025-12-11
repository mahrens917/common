"""Field reset application logic."""

import logging
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)


class FieldResetApplicator:
    """Applies reset logic to field values."""

    # Fields that should be cleared (set to None/empty) on reset
    CLEAR_ON_RESET_FIELDS: Set[str] = {
        "t_yes_bid",
        "t_yes_ask",
        "weather_explanation",
        "last_rule_applied",
        "maxT",
        "minT",
        "maxT24",
        "minT24",
    }

    def apply_reset_logic(self, field_name: str, current_value: Any, previous_data: Dict[str, Any], was_reset: bool) -> Any:
        """
        Apply reset logic to a field value.

        Args:
            field_name: Name of the field
            current_value: Current value for the field
            previous_data: Previous data to check against
            was_reset: Whether reset is needed

        Returns:
            Final value after applying reset logic
        """
        if was_reset:
            return self._apply_reset_value(field_name, current_value)
        else:
            return self._preserve_existing_value(field_name, current_value, previous_data)

    def _apply_reset_value(self, field_name: str, current_value: Any) -> Any:
        """Apply reset value (either clear or set to current)."""
        if field_name in self.CLEAR_ON_RESET_FIELDS:
            logger.info(f"🔄 DAWN RESET: Clearing field '{field_name}' to None (new trading day)")
            return None
        else:
            logger.info(f"🔄 DAWN RESET: Resetting field '{field_name}' to current value {current_value} (new trading day)")
            return current_value

    def _preserve_existing_value(self, field_name: str, current_value: Any, previous_data: Dict[str, Any]) -> Any:
        """Preserve existing value when no reset is needed."""
        if field_name in previous_data and current_value is None:
            previous_value = previous_data[field_name]
            logger.debug(f"📋 SAME DAY: Kept previous value for '{field_name}': {previous_value}")
            return previous_value
        else:
            logger.debug(f"📋 SAME DAY: Using current value for '{field_name}': {current_value}")
            return current_value
