"""Validation helpers for portfolio-related data models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Error messages
ERR_LAST_UPDATED_NOT_DATETIME_PORT = "Last updated must be a datetime object (TypeError)"

# Constants
_CONST_100 = 100


def validate_portfolio_balance(balance_cents: int, currency: str, timestamp: Any) -> None:
    """
    Validate portfolio balance data integrity.

    Args:
        balance_cents: Balance value in cents
        currency: Currency code
        timestamp: Balance timestamp

    Raises:
        ValueError: If any validation fails
    """
    if balance_cents < 0:
        raise ValueError(f"Portfolio balance cannot be negative: {balance_cents}")

    if not currency:
        raise ValueError("Currency must be specified")

    if currency != "USD":
        raise ValueError(f"Only USD currency supported, got: {currency}")

    if not isinstance(timestamp, datetime):
        raise TypeError("Timestamp must be a datetime object")


def validate_position_ticker(ticker: str) -> None:
    """
    Validate position ticker is non-empty.

    Args:
        ticker: Market ticker symbol

    Raises:
        ValueError: If ticker is empty
    """
    if not ticker:
        raise ValueError("Ticker must be specified")


def validate_position_count(position_count: int | None) -> None:
    """
    Validate position count is non-zero.

    Args:
        position_count: Number of contracts

    Raises:
        ValueError: If count is zero
    """
    if position_count is None:
        raise ValueError("Position count must be specified")

    if position_count == 0:
        raise ValueError("Position count cannot be zero")


def validate_position_side(side: Any | None) -> None:
    """
    Validate position side is OrderSide enum.

    Args:
        side: Position side (YES/NO)

    Raises:
        TypeError: If side is not OrderSide enum
    """
    from ..trading import OrderSide

    if side is None:
        raise TypeError("Side must be specified")

    if not isinstance(side, OrderSide):
        raise TypeError(f"Side must be OrderSide enum, got: {type(side)}")


def validate_position_price(average_price_cents: int | None) -> None:
    """
    Validate position average price is within valid bounds.

    Args:
        average_price_cents: Average entry price in cents

    Raises:
        ValueError: If price is out of bounds (1-100 cents)
    """
    if average_price_cents is None:
        raise ValueError("Average price must be specified")

    if average_price_cents <= 0 or average_price_cents > _CONST_100:
        raise ValueError(f"Average price must be between 1-100 cents: {average_price_cents}")


def validate_position_timestamp(last_updated: Any) -> None:
    """
    Validate position timestamp is datetime object.

    Args:
        last_updated: Position update timestamp

    Raises:
        TypeError: If timestamp is not datetime
    """
    if last_updated is None or not isinstance(last_updated, datetime):
        raise TypeError(ERR_LAST_UPDATED_NOT_DATETIME_PORT)


def validate_portfolio_position(
    ticker: str,
    position_count: int | None,
    side: Any | None,
    average_price_cents: int | None,
    last_updated: datetime | None,
) -> None:
    """
    Validate complete portfolio position data.

    Args:
        ticker: Market ticker symbol
        position_count: Number of contracts
        side: Position side (YES/NO)
        average_price_cents: Average entry price in cents
        last_updated: Position update timestamp

    Raises:
        ValueError: If any validation fails
    """
    validate_position_ticker(ticker)
    validate_position_count(position_count)
    validate_position_side(side)
    validate_position_price(average_price_cents)
    validate_position_timestamp(last_updated)
