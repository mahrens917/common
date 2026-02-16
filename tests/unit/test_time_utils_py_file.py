"""Tests for time_utils.py file (not the package)."""

from common import time_utils


def test_time_utils_py_file_all_exports():
    """Test that time_utils.py __all__ contains all expected exports."""
    time_utils_module = time_utils

    assert hasattr(time_utils_module, "__all__")
    expected = [
        "AstronomicalComputationError",
        "TimezoneLookupError",
        "DERIBIT_EXPIRY_HOUR",
        "EPOCH_START",
        "DateTimeExpiry",
        "calculate_time_to_expiry_years",
        "find_closest_expiry",
        "format_time_key",
        "get_datetime_from_time_point",
        "get_fixed_time_point",
        "get_time_from_epoch",
        "get_timezone_finder",
        "is_market_expired",
        "match_expiries_exactly",
        "parse_iso_datetime",
        "parse_timestamp",
        "resolve_timezone",
        "shutdown_timezone_finder",
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
    ]
    assert set(time_utils_module.__all__) == set(expected)


def test_time_utils_py_file_has_exports():
    """Test that time_utils.py exports all expected items."""
    time_utils_module = time_utils

    # Test a few key exports to ensure imports work
    assert hasattr(time_utils_module, "DERIBIT_EXPIRY_HOUR")
    assert hasattr(time_utils_module, "EPOCH_START")
    assert hasattr(time_utils_module, "AstronomicalComputationError")
    assert hasattr(time_utils_module, "DateTimeExpiry")
    assert hasattr(time_utils_module, "calculate_dawn_utc")
    assert hasattr(time_utils_module, "parse_timestamp")
