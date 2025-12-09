"""Order-specific validation helpers."""

from datetime import datetime
from typing import Any, Dict

from .field_validators import validate_string_field

# Constants
_MAX_PRICE = 99


def validate_order_strings(order_data: Dict[str, Any]) -> None:
    """Validate string fields in order data."""
    string_fields = ["order_id", "market_ticker", "side", "type", "action", "created_time"]
    for field in string_fields:
        validate_string_field(order_data, field)


def validate_order_enum_fields(order_data: Dict[str, Any]) -> None:
    """Validate enum-like fields have valid values."""
    if order_data["side"] not in ["yes", "no"]:
        raise ValueError(f"Invalid side '{order_data['side']}'. Must be 'yes' or 'no'")

    if order_data["type"] not in ["limit", "market"]:
        raise ValueError(f"Invalid type '{order_data['type']}'. Must be 'limit' or 'market'")

    if order_data["action"] not in ["buy", "sell"]:
        raise ValueError(f"Invalid action '{order_data['action']}'. Must be 'buy' or 'sell'")


def validate_order_numeric_fields(order_data: Dict[str, Any]) -> None:
    """Validate numeric fields in order data."""
    if not isinstance(order_data["count"], int):
        raise TypeError(f"count must be integer, got: {type(order_data['count'])}")
    if order_data["count"] <= 0:
        raise ValueError(f"count must be positive: {order_data['count']}")


def validate_order_timestamps(order_data: Dict[str, Any]) -> None:
    """Validate timestamp fields in order data."""
    try:
        datetime.fromisoformat(order_data["created_time"].replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid created_time format: {order_data['created_time']}") from e

    if "expiration_time" in order_data and order_data["expiration_time"]:
        try:
            datetime.fromisoformat(order_data["expiration_time"].replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"Invalid expiration_time format: {order_data['expiration_time']}"
            ) from e


def validate_order_prices(order_data: Dict[str, Any]) -> None:
    """Validate price fields for limit orders."""
    if order_data["type"] == "limit":
        if order_data["side"] == "yes":
            price_field = "yes_price"
        else:
            price_field = "no_price"

        if price_field not in order_data:
            raise ValueError(f"Limit order must have {price_field}")

        price = order_data[price_field]
        if not isinstance(price, (int, float)):
            raise TypeError(f"{price_field} must be numeric, got: {type(price)}")
        if price < 1 or price > _MAX_PRICE:
            raise ValueError(f"{price_field} must be between 1-99 cents, got: {price}")
