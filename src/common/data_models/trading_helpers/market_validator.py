"""Validation helpers for market validation data models."""

from datetime import datetime
from typing import Any, Optional

# Error messages
ERR_MARKET_ID_MISSING = "Market ID must be specified"
ERR_MARKET_SYMBOL_MISSING = "Market symbol must be specified"


# Constants
_MAX_PRICE = 99


def validate_market_ticker(ticker: str) -> None:
    """
    Validate market ticker is non-empty.

    Args:
        ticker: Market ticker symbol

    Raises:
        ValueError: If ticker is empty
    """
    if not ticker:
        raise ValueError("Ticker must be specified")


def validate_market_open_status(is_open: Any) -> None:
    """
    Validate market open status is boolean.

    Args:
        is_open: Whether market is currently open

    Raises:
        TypeError: If is_open is not boolean
    """
    if not isinstance(is_open, bool):
        raise TypeError("Market open status must be boolean")


def validate_bid_price(best_bid_cents: Optional[int]) -> None:
    """
    Validate best bid price if present.

    Args:
        best_bid_cents: Current best bid price in cents

    Raises:
        ValueError: If bid price is out of valid range (1-99 cents)
    """
    if best_bid_cents is None:
        return

    if best_bid_cents <= 0 or best_bid_cents > _MAX_PRICE:
        raise ValueError(f"Best bid must be between 1-99 cents: {best_bid_cents}")


def validate_ask_price(best_ask_cents: Optional[int]) -> None:
    """
    Validate best ask price if present.

    Args:
        best_ask_cents: Current best ask price in cents

    Raises:
        ValueError: If ask price is out of valid range (1-99 cents)
    """
    if best_ask_cents is None:
        return

    if best_ask_cents <= 0 or best_ask_cents > _MAX_PRICE:
        raise ValueError(f"Best ask must be between 1-99 cents: {best_ask_cents}")


def validate_bid_ask_spread(best_bid_cents: Optional[int], best_ask_cents: Optional[int]) -> None:
    """
    Validate bid-ask spread is valid (bid < ask).

    Args:
        best_bid_cents: Current best bid price in cents
        best_ask_cents: Current best ask price in cents

    Raises:
        ValueError: If bid >= ask
    """
    if best_bid_cents is None or best_ask_cents is None:
        return

    if best_bid_cents >= best_ask_cents:
        raise ValueError(
            f"Best bid ({best_bid_cents}) must be less than best ask ({best_ask_cents})"
        )


def validate_last_price(last_price_cents: Optional[int]) -> None:
    """
    Validate last price if present.

    Args:
        last_price_cents: Most recent trade price in cents

    Raises:
        ValueError: If last price is out of valid range (1-99 cents)
    """
    if last_price_cents is None:
        return

    if last_price_cents <= 0 or last_price_cents > _MAX_PRICE:
        raise ValueError(f"Last price must be between 1-99 cents: {last_price_cents}")


def validate_market_timestamp(timestamp: Any) -> None:
    """
    Validate market data timestamp is datetime object.

    Args:
        timestamp: Market data collection timestamp

    Raises:
        TypeError: If timestamp is not datetime
    """
    if not isinstance(timestamp, datetime):
        raise TypeError("Market data timestamp must be a datetime object")


def validate_market_validation_data(
    ticker: str,
    is_open: bool,
    best_bid_cents: Optional[int],
    best_ask_cents: Optional[int],
    last_price_cents: Optional[int],
    timestamp: datetime,
) -> None:
    """
    Validate complete market validation data.

    Args:
        ticker: Market ticker symbol
        is_open: Whether market is currently open
        best_bid_cents: Current best bid price in cents
        best_ask_cents: Current best ask price in cents
        last_price_cents: Most recent trade price in cents
        timestamp: Market data collection timestamp

    Raises:
        ValueError: If any validation fails
    """
    validate_market_ticker(ticker)
    validate_market_open_status(is_open)
    validate_bid_price(best_bid_cents)
    validate_ask_price(best_ask_cents)
    validate_bid_ask_spread(best_bid_cents, best_ask_cents)
    validate_last_price(last_price_cents)
    validate_market_timestamp(timestamp)
