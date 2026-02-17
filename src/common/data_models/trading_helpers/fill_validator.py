"""Validation helpers for order fill data models."""

from datetime import datetime
from typing import Any

from common.constants.trading import MAX_PRICE_CENTS

# Error messages
ERR_FILL_QUANTITY_NOT_POSITIVE = "Fill quantity must be positive: {value}"
ERR_FILL_PRICE_NOT_POSITIVE = "Fill price must be positive: {value}"


def validate_fill_price(price_cents: int) -> None:
    """
    Validate fill price is within valid bounds.

    Args:
        price_cents: Fill execution price in cents

    Raises:
        ValueError: If price is out of bounds (1-99 cents)
    """
    if price_cents <= 0 or price_cents > MAX_PRICE_CENTS:
        raise ValueError(f"Fill price must be between 1-99 cents: {price_cents}")


def validate_fill_count(count: int) -> None:
    """
    Validate fill count is positive.

    Args:
        count: Number of contracts filled

    Raises:
        ValueError: If count is not positive
    """
    if count <= 0:
        raise ValueError(f"Fill count must be positive: {count}")


def validate_fill_timestamp(timestamp: Any) -> None:
    """
    Validate fill timestamp is datetime object.

    Args:
        timestamp: Fill execution timestamp

    Raises:
        TypeError: If timestamp is not datetime
    """
    if not isinstance(timestamp, datetime):
        raise TypeError("Fill timestamp must be a datetime object")


def validate_order_fill(price_cents: int, count: int, timestamp: datetime) -> None:
    """
    Validate complete order fill data.

    Args:
        price_cents: Fill execution price in cents
        count: Number of contracts filled
        timestamp: Fill execution timestamp

    Raises:
        ValueError: If any validation fails
    """
    validate_fill_price(price_cents)
    validate_fill_count(count)
    validate_fill_timestamp(timestamp)
