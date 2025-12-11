"""
Pricing utilities for market data calculations.

This module provides centralized pricing functions for market data calculations.
All pricing calculations should use these centralized functions to maintain
consistency across the application.

ARCHITECTURAL DESIGN:
- Separate bid/ask calculations for surface-related operations
- Micro price calculations for bid/ask agnostic operations (moneyness, alerts, etc.)
- All functions fail-fast with explicit error handling
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def calculate_usdc_micro_price(bid_price: float, ask_price: float, bid_size: float, ask_size: float) -> float:
    """
    Calculate volume-weighted micro price from BTC_USDC/ETH_USDC bid/ask data.

    This is the authoritative mid-price calculation for bid/ask agnostic operations
    such as strike moneyness calculations, price alerts, and trading analysis.

    Formula: (bid_price * ask_size + ask_price * bid_size) / (bid_size + ask_size)

    Args:
        bid_price: Best bid price from USDC pair
        ask_price: Best ask price from USDC pair
        bid_size: Size at best bid
        ask_size: Size at best ask

    Returns:
        Volume-weighted micro price as float

    Raises:
        ValueError: If prices are invalid (non-positive or bid > ask)
        ValueError: If sizes are invalid (negative)
    """
    # Validate inputs - fail fast on invalid data
    if bid_price <= 0:
        raise ValueError(f"Invalid bid price: {bid_price}. Must be positive.")
    if ask_price <= 0:
        raise ValueError(f"Invalid ask price: {ask_price}. Must be positive.")
    if bid_price > ask_price:
        raise ValueError(f"Invalid spread: bid {bid_price} > ask {ask_price}")
    if bid_size < 0:
        raise ValueError(f"Invalid bid size: {bid_size}. Must be non-negative.")
    if ask_size < 0:
        raise ValueError(f"Invalid ask size: {ask_size}. Must be non-negative.")

    # Calculate total size
    total_size = bid_size + ask_size

    if total_size == 0:
        raise ValueError("Total order book size must be positive to compute micro price.")

    # Volume-weighted calculation
    micro_price = (bid_price * ask_size + ask_price * bid_size) / total_size

    logger.debug(
        f"Calculated micro price: {micro_price:.6f} from bid={bid_price}, ask={ask_price}, " f"bid_size={bid_size}, ask_size={ask_size}"
    )

    return micro_price


def validate_usdc_bid_ask_prices(bid_price: float, ask_price: float) -> Tuple[float, float]:
    """
    Validate USDC bid/ask prices for surface calculations.

    Used for bid/ask surface operations where separate bid and ask prices
    are required (futures curves, option conversion, probability extraction).

    Args:
        bid_price: Best bid price from USDC pair
        ask_price: Best ask price from USDC pair

    Returns:
        Tuple of (validated_bid_price, validated_ask_price)

    Raises:
        ValueError: If prices are invalid (non-positive or bid > ask)
    """
    # Validate inputs - fail fast on invalid data
    if bid_price <= 0:
        raise ValueError(f"Invalid bid price: {bid_price}. Must be positive.")
    if ask_price <= 0:
        raise ValueError(f"Invalid ask price: {ask_price}. Must be positive.")
    if bid_price > ask_price:
        raise ValueError(f"Invalid spread: bid {bid_price} > ask {ask_price}")

    logger.debug(f"Validated USDC bid/ask prices: bid={bid_price}, ask={ask_price}")

    return bid_price, ask_price


def calculate_price_change_percentage(old_price: float, new_price: float) -> float:
    """
    Calculate percentage change between two prices.

    Used for price alert calculations and monitoring.

    Args:
        old_price: Previous price
        new_price: Current price

    Returns:
        Percentage change as float (e.g., 5.0 for 5% increase)

    Raises:
        ValueError: If old_price is non-positive
        ValueError: If new_price is non-positive
    """
    if old_price <= 0:
        raise ValueError(f"Invalid old price: {old_price}. Must be positive.")
    if new_price <= 0:
        raise ValueError(f"Invalid new price: {new_price}. Must be positive.")

    percentage_change = ((new_price - old_price) / old_price) * 100

    logger.debug(f"Price change: {old_price} -> {new_price} = {percentage_change:.2f}%")

    return percentage_change


def calculate_strike_moneyness_ratio(strike_price: float, spot_price: float) -> float:
    """
    Calculate strike-to-spot moneyness ratio for option categorization.

    Used for grid categorization and option analysis.

    Args:
        strike_price: Option strike price
        spot_price: Current spot price (should be USDC micro price)

    Returns:
        Moneyness ratio as float (e.g., 1.05 for 5% OTM call)

    Raises:
        ValueError: If either price is non-positive
    """
    if strike_price <= 0:
        raise ValueError(f"Invalid strike price: {strike_price}. Must be positive.")
    if spot_price <= 0:
        raise ValueError(f"Invalid spot price: {spot_price}. Must be positive.")

    moneyness_ratio = strike_price / spot_price

    logger.debug(f"Strike moneyness: {strike_price} / {spot_price} = {moneyness_ratio:.4f}")

    return moneyness_ratio
