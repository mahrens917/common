"""Maps reset fields to their corresponding timestamp fields."""


class TimestampMapper:
    """Maps field names to timestamp fields used for reset checking."""

    def get_timestamp_field_for_reset_field(self, field_name: str) -> str:
        """
        Get the timestamp field name that should be used to check reset for a given field.

        Args:
            field_name: Name of the field to get timestamp for

        Returns:
            Name of the timestamp field to use for reset checking
        """
        # Map fields to their relevant timestamp fields
        timestamp_mapping = {
            "max_temp_f": "max_start_time",
            "max_start_time": "max_start_time",
            "daily_max_state": "max_start_time",  # Bounds state tied to max temp timing
            "t_yes_bid": "last_updated",
            "t_yes_ask": "last_updated",
            "weather_explanation": "last_updated",
            "last_rule_applied": "last_updated",
        }

        default_field = "last_updated"
        return timestamp_mapping[field_name] if field_name in timestamp_mapping else default_field
