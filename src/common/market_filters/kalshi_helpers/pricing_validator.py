"""Pricing validation helpers for Kalshi markets."""

from typing import Optional, Tuple


def check_side_validity(price: Optional[float], size: Optional[int]) -> bool:
    """Check if a bid/ask side has valid data."""
    return price is not None and price >= 0.0 and size is not None


def validate_pricing_data(
    bid_price: Optional[float],
    bid_size: Optional[int],
    ask_price: Optional[float],
    ask_size: Optional[int],
    require_pricing: bool,
) -> Tuple[bool, Optional[str]]:
    """
    Validate pricing data meets requirements.

    Returns: (is_valid, reason)
    """
    has_bid = check_side_validity(bid_price, bid_size)
    has_ask = check_side_validity(ask_price, ask_size)

    has_pricing = has_bid or has_ask

    if require_pricing and not has_pricing:
        return False, "missing_pricing_data"

    return True, None
