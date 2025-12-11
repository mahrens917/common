"""Market-specific validation helpers."""

from typing import Any, Dict

from .field_validators import (
    validate_numeric_field,
    validate_string_field,
    validate_timestamp_field,
)

# Constants
_CONST_100 = 100


def validate_market_strings(market_data: Dict[str, Any], prefix: str = "") -> None:
    """Validate all string fields in market data."""
    string_fields = ["ticker", "event_ticker", "title", "status"]
    for field in string_fields:
        validate_string_field(market_data, field, prefix)


def validate_market_status(market_data: Dict[str, Any], prefix: str = "") -> None:
    """Validate market status is a known value."""
    valid_statuses = ["open", "closed", "settled", "active"]
    if market_data["status"] not in valid_statuses:
        raise ValueError(f"{prefix}Invalid status '{market_data['status']}'. " f"Valid statuses: {valid_statuses}")


def validate_market_timestamps(market_data: Dict[str, Any], prefix: str = "") -> None:
    """Validate all timestamp fields in market data."""
    for time_field in ["open_time", "close_time"]:
        validate_timestamp_field(market_data, time_field, prefix)


def validate_market_numeric_fields(market_data: Dict[str, Any], prefix: str = "") -> None:
    """Validate volume and other numeric fields."""
    numeric_fields = ["volume", "volume_24h"]
    for field in numeric_fields:
        validate_numeric_field(market_data, field, prefix)


def validate_market_price_fields(market_data: Dict[str, Any], prefix: str = "") -> None:
    """Validate optional price fields if present."""
    price_fields = ["yes_bid", "yes_ask", "no_bid", "no_ask", "last_price"]
    for field in price_fields:
        if field in market_data and market_data[field] is not None:
            if not isinstance(market_data[field], (int, float)):
                raise TypeError(f"{prefix}{field} must be numeric or null, got: {type(market_data[field])}")
            if market_data[field] < 0 or market_data[field] > _CONST_100:
                raise ValueError(f"{prefix}{field} must be between 0-100 cents, got: {market_data[field]}")
