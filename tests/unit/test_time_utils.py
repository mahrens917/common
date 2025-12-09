"""Tests for the time_utils module re-exports."""

from __future__ import annotations


class TestTimeUtilsReexports:
    """Test that time_utils properly re-exports all expected symbols."""

    def test_expiry_constants_exported(self) -> None:
        """Test that expiry constants are exported."""
        from src.common.time_utils import DERIBIT_EXPIRY_HOUR, EPOCH_START

        assert DERIBIT_EXPIRY_HOUR is not None
        assert EPOCH_START is not None

    def test_datetime_expiry_class_exported(self) -> None:
        """Test that DateTimeExpiry class is exported."""
        from src.common.time_utils import DateTimeExpiry

        assert DateTimeExpiry is not None

    def test_expiry_functions_exported(self) -> None:
        """Test that expiry functions are exported."""
        from src.common.time_utils import (
            calculate_time_to_expiry_years,
            find_closest_expiry,
            format_time_key,
            get_datetime_from_time_point,
            get_fixed_time_point,
            get_time_from_epoch,
            is_market_expired,
            match_expiries_exactly,
            parse_iso_datetime,
            validate_expiry_hour,
        )

        assert callable(calculate_time_to_expiry_years)
        assert callable(find_closest_expiry)
        assert callable(format_time_key)
        assert callable(get_datetime_from_time_point)
        assert callable(get_fixed_time_point)
        assert callable(get_time_from_epoch)
        assert callable(is_market_expired)
        assert callable(match_expiries_exactly)
        assert callable(parse_iso_datetime)
        assert callable(validate_expiry_hour)

    def test_timezone_functions_exported(self) -> None:
        """Test that timezone functions are exported."""
        from src.common.time_utils import (
            ensure_timezone_aware,
            format_datetime,
            get_current_date_in_timezone,
            get_current_est,
            get_current_utc,
            get_days_ago_utc,
            get_start_of_day_utc,
            get_timezone_aware_date,
            load_configured_timezone,
            sleep_until_next_minute,
            to_utc,
        )

        assert callable(ensure_timezone_aware)
        assert callable(format_datetime)
        assert callable(get_current_date_in_timezone)
        assert callable(get_current_est)
        assert callable(get_current_utc)
        assert callable(get_days_ago_utc)
        assert callable(get_start_of_day_utc)
        assert callable(get_timezone_aware_date)
        assert callable(load_configured_timezone)
        assert callable(sleep_until_next_minute)
        assert callable(to_utc)

    def test_location_function_exported(self) -> None:
        """Test that location function is exported."""
        from src.common.time_utils import get_timezone_from_coordinates

        assert callable(get_timezone_from_coordinates)

    def test_timestamp_parser_exported(self) -> None:
        """Test that timestamp parser is exported."""
        from src.common.time_utils import parse_timestamp

        assert callable(parse_timestamp)

    def test_astronomical_functions_exported(self) -> None:
        """Test that astronomical computation functions are exported."""
        from src.common.time_utils import (
            calculate_dawn_utc,
            calculate_dusk_utc,
            calculate_local_midnight_utc,
            calculate_solar_noon_utc,
            is_after_local_midnight,
            is_after_midpoint_noon_to_dusk,
            is_after_solar_noon,
            is_between_dawn_and_dusk,
        )

        assert callable(calculate_dawn_utc)
        assert callable(calculate_dusk_utc)
        assert callable(calculate_local_midnight_utc)
        assert callable(calculate_solar_noon_utc)
        assert callable(is_after_local_midnight)
        assert callable(is_after_midpoint_noon_to_dusk)
        assert callable(is_after_solar_noon)
        assert callable(is_between_dawn_and_dusk)

    def test_astronomical_error_exported(self) -> None:
        """Test that AstronomicalComputationError is exported."""
        from src.common.time_utils import AstronomicalComputationError

        assert issubclass(AstronomicalComputationError, Exception)

    def test_all_attribute_complete(self) -> None:
        """Test that __all__ contains all expected exports."""
        from src.common import time_utils

        expected_exports = {
            "AstronomicalComputationError",
            "DERIBIT_EXPIRY_HOUR",
            "EPOCH_START",
            "DateTimeExpiry",
            "calculate_time_to_expiry_years",
            "find_closest_expiry",
            "format_time_key",
            "get_datetime_from_time_point",
            "get_fixed_time_point",
            "get_time_from_epoch",
            "is_market_expired",
            "match_expiries_exactly",
            "parse_iso_datetime",
            "parse_timestamp",
            "validate_expiry_hour",
            "ensure_timezone_aware",
            "format_datetime",
            "get_current_date_in_timezone",
            "get_current_est",
            "get_current_utc",
            "get_days_ago_utc",
            "get_start_of_day_utc",
            "get_timezone_aware_date",
            "load_configured_timezone",
            "sleep_until_next_minute",
            "to_utc",
            "calculate_solar_noon_utc",
            "is_after_solar_noon",
            "get_timezone_from_coordinates",
            "calculate_local_midnight_utc",
            "is_after_local_midnight",
            "calculate_dawn_utc",
            "calculate_dusk_utc",
            "is_between_dawn_and_dusk",
            "is_after_midpoint_noon_to_dusk",
        }
        assert set(time_utils.__all__) == expected_exports
