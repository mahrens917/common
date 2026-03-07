"""Field-level validation for micro price option data."""

from typing import Optional

from .validation_params import BasicOptionData


def validate_strike(strike: float) -> None:
    """Validate strike price."""
    if strike <= 0:
        raise TypeError(f"Strike price must be positive: {strike}")


def validate_prices(best_bid: float, best_ask: float) -> None:
    """Validate bid and ask prices."""
    if best_bid < 0:
        raise ValueError(f"Bid price cannot be negative: {best_bid}")
    if best_ask < 0:
        raise ValueError(f"Ask price cannot be negative: {best_ask}")
    if best_ask < best_bid:
        raise TypeError(f"Ask price ({best_ask}) must be >= bid price ({best_bid})")


def validate_sizes(best_bid_size: Optional[float], best_ask_size: Optional[float]) -> None:
    """Validate bid and ask sizes."""
    if best_bid_size is not None and best_bid_size < 0:
        raise ValueError(f"Bid size cannot be negative: {best_bid_size}")
    if best_ask_size is not None and best_ask_size < 0:
        raise ValueError(f"Ask size cannot be negative: {best_ask_size}")


def validate_option_type(option_type: str) -> None:
    """Validate option type."""
    if option_type not in ["call", "put"]:
        raise TypeError(f"Option type must be 'call' or 'put': {option_type}")


def validate_forward_price(forward_price: float) -> None:
    """Validate forward price."""
    if forward_price <= 0.0:
        raise ValueError(f"Forward price must be positive when provided: {forward_price}")


def validate_discount_factor(discount_factor: float) -> None:
    """Validate discount factor."""
    if discount_factor <= 0.0:
        raise ValueError(f"Discount factor must be positive when provided: {discount_factor}")


def validate_basic_option_data(params: BasicOptionData) -> None:
    """Validate basic option data constraints."""
    validate_strike(params.strike)
    validate_prices(params.best_bid, params.best_ask)
    validate_sizes(params.best_bid_size, params.best_ask_size)
    validate_option_type(params.option_type)

    if params.forward_price is not None:
        validate_forward_price(params.forward_price)
    if params.discount_factor is not None:
        validate_discount_factor(params.discount_factor)
