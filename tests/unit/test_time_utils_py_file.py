"""Tests for time_utils.py file (not the package)."""

import importlib.util
import sys
from pathlib import Path


def test_time_utils_py_file_all_exports():
    """Test that time_utils.py __all__ contains all expected exports."""
    module_path = Path("/Users/mahrens917/common/src/common/time_utils.py")
    spec = importlib.util.spec_from_file_location("time_utils_py_file", module_path)
    assert spec is not None
    assert spec.loader is not None
    time_utils_module = importlib.util.module_from_spec(spec)
    sys.modules["time_utils_py_file"] = time_utils_module
    spec.loader.exec_module(time_utils_module)

    assert hasattr(time_utils_module, "__all__")
    expected = [
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
    ]
    assert set(time_utils_module.__all__) == set(expected)


def test_time_utils_py_file_has_exports():
    """Test that time_utils.py exports all expected items."""
    module_path = Path("/Users/mahrens917/common/src/common/time_utils.py")
    spec = importlib.util.spec_from_file_location("time_utils_py_file2", module_path)
    assert spec is not None
    assert spec.loader is not None
    time_utils_module = importlib.util.module_from_spec(spec)
    sys.modules["time_utils_py_file2"] = time_utils_module
    spec.loader.exec_module(time_utils_module)

    # Test a few key exports to ensure imports work
    assert hasattr(time_utils_module, "DERIBIT_EXPIRY_HOUR")
    assert hasattr(time_utils_module, "EPOCH_START")
    assert hasattr(time_utils_module, "AstronomicalComputationError")
    assert hasattr(time_utils_module, "DateTimeExpiry")
    assert hasattr(time_utils_module, "calculate_dawn_utc")
    assert hasattr(time_utils_module, "parse_timestamp")
