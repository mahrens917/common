"""Kalshi-specific price validation.

Provides validation for Kalshi market prices (0-100 cents range).
"""

from typing import Optional

# Price bounds for Kalshi markets (in cents)
KALSHI_MAX_PRICE_CENTS = 100.0
KALSHI_MIN_PRICE_CENTS = 0.0


def validate_kalshi_bid_ask_relationship(bid: Optional[float], ask: Optional[float]) -> None:
    """
    Validate bid <= ask relationship for Kalshi markets.

    Args:
        bid: Bid price in cents
        ask: Ask price in cents

    Raises:
        RuntimeError: If bid > ask
    """
    if bid is not None and ask is not None and bid > ask:
        raise RuntimeError(f"Invalid Kalshi market: bid {bid} > ask {ask}")


def validate_kalshi_price_bounds(price: float, field_name: str = "price") -> None:
    """
    Validate price is within Kalshi's acceptable range (0-100 cents).

    Args:
        price: Price to validate in cents
        field_name: Name of field for error messages

    Raises:
        TypeError: If price is negative
        ValueError: If price exceeds maximum
    """
    if price < KALSHI_MIN_PRICE_CENTS:
        raise TypeError(f"{field_name} must be non-negative, got {price}")
    if price > KALSHI_MAX_PRICE_CENTS:
        raise ValueError(f"{field_name} exceeds maximum of {KALSHI_MAX_PRICE_CENTS} cents, got {price}")


def validate_kalshi_price_pair(bid: Optional[float], ask: Optional[float]) -> None:
    """
    Validate a Kalshi bid/ask price pair.

    Checks both individual price bounds and bid <= ask relationship.

    Args:
        bid: Bid price in cents
        ask: Ask price in cents

    Raises:
        TypeError: If any price is negative
        ValueError: If any price exceeds maximum
        RuntimeError: If bid > ask
    """
    if bid is not None:
        validate_kalshi_price_bounds(bid, "bid")
    if ask is not None:
        validate_kalshi_price_bounds(ask, "ask")
    validate_kalshi_bid_ask_relationship(bid, ask)


__all__ = [
    "KALSHI_MAX_PRICE_CENTS",
    "KALSHI_MIN_PRICE_CENTS",
    "validate_kalshi_bid_ask_relationship",
    "validate_kalshi_price_bounds",
    "validate_kalshi_price_pair",
]
