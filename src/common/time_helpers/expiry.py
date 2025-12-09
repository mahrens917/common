from __future__ import annotations

"""Expiry and epoch related utilities (Refactored)."""

_PRE_EPOCH_CLAMP_LOGGED = False


# Re-export conversion functions
from .expiry_conversions import (
    DERIBIT_EXPIRY_HOUR,
    EPOCH_START,
    calculate_time_to_expiry_years,
    format_time_key,
    get_datetime_from_time_point,
    get_fixed_time_point,
    get_time_from_epoch,
    is_market_expired,
    parse_iso_datetime,
    validate_expiry_hour,
)

# Re-export matching functions
from .expiry_matching import find_closest_expiry, match_expiries_exactly

# Re-export DateTimeExpiry class
from .expiry_wrapper import DateTimeExpiry

__all__ = [
    "EPOCH_START",
    "DERIBIT_EXPIRY_HOUR",
    "validate_expiry_hour",
    "calculate_time_to_expiry_years",
    "get_time_from_epoch",
    "get_datetime_from_time_point",
    "parse_iso_datetime",
    "get_fixed_time_point",
    "format_time_key",
    "is_market_expired",
    "DateTimeExpiry",
    "find_closest_expiry",
    "match_expiries_exactly",
]
