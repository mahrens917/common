from __future__ import annotations

"""Common time calculation utilities."""

from ..time_helpers.expiry import (
    DERIBIT_EXPIRY_HOUR,
    EPOCH_START,
    DateTimeExpiry,
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
from ..time_helpers.location import (
    TimezoneLookupError,
    get_timezone_finder,
    resolve_timezone,
    shutdown_timezone_finder,
)
from ..time_helpers.timestamp_parser import parse_timestamp
from ..time_helpers.timezone import (
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
from .base import AstronomicalComputationError
from .local import (
    calculate_local_midnight_utc,
    get_timezone_from_coordinates,
    is_after_local_midnight,
)
from .solar import calculate_solar_noon_utc, is_after_solar_noon
from .twilight import (
    calculate_dawn_utc,
    calculate_dusk_utc,
    is_after_midpoint_noon_to_dusk,
    is_between_dawn_and_dusk,
)

__all__ = [
    # Exceptions
    "AstronomicalComputationError",
    "TimezoneLookupError",
    # Timezone finder utilities
    "get_timezone_finder",
    "resolve_timezone",
    "shutdown_timezone_finder",
    # Re-exported expiry helpers
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
    "validate_expiry_hour",
    # Re-exported timezone helpers
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
    "parse_timestamp",
    # Local utilities
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
