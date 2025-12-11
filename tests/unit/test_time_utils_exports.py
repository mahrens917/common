"""Tests for re-exported time utilities."""

from common import time_utils as time_utils_module


def test_time_utils_exports_constants():
    assert hasattr(time_utils_module, "DERIBIT_EXPIRY_HOUR")
    assert hasattr(time_utils_module, "EPOCH_START")


def test_time_utils_exports_functions():
    assert time_utils_module.parse_timestamp("2025-01-01T00:00:00Z")
    assert time_utils_module.format_time_key(0)
    assert time_utils_module.get_timezone_from_coordinates(0.0, 0.0)


def test_time_utils_all_imports_work():
    """Test that importing from time_utils works for all __all__ items."""
    from common.time_utils import (
        DERIBIT_EXPIRY_HOUR,
        EPOCH_START,
        AstronomicalComputationError,
        DateTimeExpiry,
        calculate_dawn_utc,
        calculate_dusk_utc,
        calculate_local_midnight_utc,
        calculate_solar_noon_utc,
        calculate_time_to_expiry_years,
        ensure_timezone_aware,
        find_closest_expiry,
        format_datetime,
        format_time_key,
        get_current_date_in_timezone,
        get_current_est,
        get_current_utc,
        get_datetime_from_time_point,
        get_days_ago_utc,
        get_fixed_time_point,
        get_start_of_day_utc,
        get_time_from_epoch,
        get_timezone_aware_date,
        get_timezone_from_coordinates,
        is_after_local_midnight,
        is_after_midpoint_noon_to_dusk,
        is_after_solar_noon,
        is_between_dawn_and_dusk,
        is_market_expired,
        load_configured_timezone,
        match_expiries_exactly,
        parse_iso_datetime,
        parse_timestamp,
        sleep_until_next_minute,
        to_utc,
        validate_expiry_hour,
    )

    # Verify constants exist
    assert DERIBIT_EXPIRY_HOUR is not None
    assert EPOCH_START is not None

    # Verify exception class
    assert issubclass(AstronomicalComputationError, Exception)

    # Verify class
    assert DateTimeExpiry is not None

    # Verify all functions are callable
    assert callable(calculate_dawn_utc)
    assert callable(calculate_dusk_utc)
    assert callable(calculate_local_midnight_utc)
    assert callable(calculate_solar_noon_utc)
    assert callable(calculate_time_to_expiry_years)
    assert callable(ensure_timezone_aware)
    assert callable(find_closest_expiry)
    assert callable(format_datetime)
    assert callable(format_time_key)
    assert callable(get_current_date_in_timezone)
    assert callable(get_current_est)
    assert callable(get_current_utc)
    assert callable(get_datetime_from_time_point)
    assert callable(get_days_ago_utc)
    assert callable(get_fixed_time_point)
    assert callable(get_start_of_day_utc)
    assert callable(get_time_from_epoch)
    assert callable(get_timezone_aware_date)
    assert callable(get_timezone_from_coordinates)
    assert callable(is_after_local_midnight)
    assert callable(is_after_midpoint_noon_to_dusk)
    assert callable(is_after_solar_noon)
    assert callable(is_between_dawn_and_dusk)
    assert callable(is_market_expired)
    assert callable(load_configured_timezone)
    assert callable(match_expiries_exactly)
    assert callable(parse_iso_datetime)
    assert callable(parse_timestamp)
    assert callable(sleep_until_next_minute)
    assert callable(to_utc)
    assert callable(validate_expiry_hour)
