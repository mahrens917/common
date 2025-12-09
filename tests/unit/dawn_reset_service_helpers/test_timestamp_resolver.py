"""Tests for timestamp resolver module."""

from datetime import datetime, timezone

from src.common.dawn_reset_service_helpers.timestamp_resolver import TimestampResolver


class TestTimestampResolverGetLastDawnResetTimestamp:
    """Tests for TimestampResolver.get_last_dawn_reset_timestamp."""

    def test_returns_none_for_missing_field(self) -> None:
        """Returns None when last_dawn_reset field is missing."""
        resolver = TimestampResolver()
        previous_data = {"other_field": "value"}

        result = resolver.get_last_dawn_reset_timestamp(previous_data)

        assert result is None

    def test_returns_none_for_none_value(self) -> None:
        """Returns None when field value is None."""
        resolver = TimestampResolver()
        previous_data = {"last_dawn_reset": None}

        result = resolver.get_last_dawn_reset_timestamp(previous_data)

        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        """Returns None when field value is empty string."""
        resolver = TimestampResolver()
        previous_data = {"last_dawn_reset": ""}

        result = resolver.get_last_dawn_reset_timestamp(previous_data)

        assert result is None

    def test_returns_none_for_none_string(self) -> None:
        """Returns None when field value is literal 'None' string."""
        resolver = TimestampResolver()
        previous_data = {"last_dawn_reset": "None"}

        result = resolver.get_last_dawn_reset_timestamp(previous_data)

        assert result is None

    def test_parses_valid_iso_timestamp(self) -> None:
        """Parses valid ISO timestamp."""
        resolver = TimestampResolver()
        previous_data = {"last_dawn_reset": "2025-01-15T08:00:00+00:00"}

        result = resolver.get_last_dawn_reset_timestamp(previous_data)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 8

    def test_parses_z_suffix_timestamp(self) -> None:
        """Parses timestamp with Z suffix."""
        resolver = TimestampResolver()
        previous_data = {"last_dawn_reset": "2025-01-15T08:00:00Z"}

        result = resolver.get_last_dawn_reset_timestamp(previous_data)

        assert result is not None
        assert result.tzinfo is not None

    def test_returns_none_for_invalid_format(self) -> None:
        """Returns None for invalid timestamp format."""
        resolver = TimestampResolver()
        previous_data = {"last_dawn_reset": "not-a-timestamp"}

        result = resolver.get_last_dawn_reset_timestamp(previous_data)

        assert result is None


class TestTimestampResolverGetTimestampFieldForResetField:
    """Tests for TimestampResolver.get_timestamp_field_for_reset_field."""

    def test_returns_max_start_time_for_max_temp_f(self) -> None:
        """Returns max_start_time for max_temp_f field."""
        resolver = TimestampResolver()

        result = resolver.get_timestamp_field_for_reset_field("max_temp_f")

        assert result == "max_start_time"

    def test_returns_max_start_time_for_daily_max_c(self) -> None:
        """Returns max_start_time for daily_max_c field."""
        resolver = TimestampResolver()

        result = resolver.get_timestamp_field_for_reset_field("daily_max_c")

        assert result == "max_start_time"

    def test_returns_max_start_time_for_hourly_max_temp_f(self) -> None:
        """Returns max_start_time for hourly_max_temp_f field."""
        resolver = TimestampResolver()

        result = resolver.get_timestamp_field_for_reset_field("hourly_max_temp_f")

        assert result == "max_start_time"

    def test_returns_last_updated_for_t_yes_bid(self) -> None:
        """Returns last_updated for t_yes_bid field."""
        resolver = TimestampResolver()

        result = resolver.get_timestamp_field_for_reset_field("t_yes_bid")

        assert result == "last_updated"

    def test_returns_last_updated_for_t_yes_ask(self) -> None:
        """Returns last_updated for t_yes_ask field."""
        resolver = TimestampResolver()

        result = resolver.get_timestamp_field_for_reset_field("t_yes_ask")

        assert result == "last_updated"

    def test_returns_last_updated_for_weather_explanation(self) -> None:
        """Returns last_updated for weather_explanation field."""
        resolver = TimestampResolver()

        result = resolver.get_timestamp_field_for_reset_field("weather_explanation")

        assert result == "last_updated"

    def test_returns_last_updated_for_last_rule_applied(self) -> None:
        """Returns last_updated for last_rule_applied field."""
        resolver = TimestampResolver()

        result = resolver.get_timestamp_field_for_reset_field("last_rule_applied")

        assert result == "last_updated"

    def test_returns_default_for_unknown_field(self) -> None:
        """Returns default last_updated for unknown field."""
        resolver = TimestampResolver()

        result = resolver.get_timestamp_field_for_reset_field("unknown_field")

        assert result == "last_updated"


class TestTimestampResolverDailyResetFields:
    """Tests for TimestampResolver.DAILY_RESET_FIELDS."""

    def test_contains_max_temp_f(self) -> None:
        """Contains max_temp_f field."""
        assert "max_temp_f" in TimestampResolver.DAILY_RESET_FIELDS

    def test_contains_max_start_time(self) -> None:
        """Contains max_start_time field."""
        assert "max_start_time" in TimestampResolver.DAILY_RESET_FIELDS

    def test_contains_daily_max_c(self) -> None:
        """Contains daily_max_c field."""
        assert "daily_max_c" in TimestampResolver.DAILY_RESET_FIELDS

    def test_contains_hourly_max_temp_f(self) -> None:
        """Contains hourly_max_temp_f field."""
        assert "hourly_max_temp_f" in TimestampResolver.DAILY_RESET_FIELDS

    def test_contains_t_yes_bid(self) -> None:
        """Contains t_yes_bid field."""
        assert "t_yes_bid" in TimestampResolver.DAILY_RESET_FIELDS

    def test_contains_weather_explanation(self) -> None:
        """Contains weather_explanation field."""
        assert "weather_explanation" in TimestampResolver.DAILY_RESET_FIELDS


class TestTimestampResolverLastDawnResetField:
    """Tests for TimestampResolver.LAST_DAWN_RESET_FIELD."""

    def test_constant_value(self) -> None:
        """Constant has expected value."""
        assert TimestampResolver.LAST_DAWN_RESET_FIELD == "last_dawn_reset"
