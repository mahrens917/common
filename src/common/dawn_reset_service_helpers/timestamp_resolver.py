"""Timestamp resolution for dawn reset service."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TimestampResolver:
    """
    Resolves timestamps from previous data for dawn reset evaluation.

    Extracts and parses timestamps from data dictionaries, handling
    different timestamp field names and formats.
    """

    # Fields that should reset at local dawn
    DAILY_RESET_FIELDS = {
        "max_temp_f",
        "max_start_time",
        "daily_max_c",
        "hourly_max_temp_f",
        "max_temp_is_exact",
        "maxT",
        "minT",
        "maxT24",
        "minT24",
        "t_bid",
        "t_ask",
        "weather_explanation",
        "last_rule_applied",
    }

    LAST_DAWN_RESET_FIELD = "last_dawn_reset"

    def get_last_dawn_reset_timestamp(self, previous_data: Dict[str, Any]) -> Optional[datetime]:
        """
        Extract the last recorded dawn reset timestamp from previous data.

        Args:
            previous_data: Previous data dictionary

        Returns:
            Last dawn reset timestamp or None if not available
        """
        raw_value = previous_data.get(self.LAST_DAWN_RESET_FIELD)
        if raw_value in (None, "", "None"):
            return None

        try:
            return datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
        except (  # policy_guard: allow-silent-handler
            ValueError,
            TypeError,
        ):
            logger.debug("🌅 INVALID LAST DAWN RESET TIMESTAMP: value=%s", raw_value)
            return None

    def get_timestamp_field_for_reset_field(self, field_name: str) -> str:
        """
        Get the timestamp field name associated with a reset field.

        Args:
            field_name: Name of the field to get timestamp for

        Returns:
            Name of the associated timestamp field
        """
        # Map reset fields to their associated timestamp fields
        timestamp_mapping = {
            "max_temp_f": "max_start_time",
            "max_start_time": "max_start_time",
            "daily_max_c": "max_start_time",
            "hourly_max_temp_f": "max_start_time",
            "t_bid": "last_updated",
            "t_ask": "last_updated",
            "weather_explanation": "last_updated",
            "last_rule_applied": "last_updated",
        }

        default_field = "last_updated"
        if field_name in timestamp_mapping:
            return timestamp_mapping[field_name]
        return default_field
