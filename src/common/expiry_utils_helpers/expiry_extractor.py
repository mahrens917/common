"""Helpers for extracting expiry from market data."""

from typing import Any, Dict, Union

from common.exceptions import DataError


def extract_expiry_from_market(market_data: Union[Dict[str, Any], Any]) -> Any:
    """
    Extract expiry from market data (handles both dict and object formats).

    Returns:
        Raw expiry value (may be string or datetime)

    Raises:
        ValueError: If no expiry field found
    """
    market_expiry = None

    if hasattr(market_data, "expiry_time"):
        # Enhanced market object format (Phase 7 style)
        market_expiry = getattr(market_data, "expiry_time")
    elif isinstance(market_data, dict):
        # Dictionary format (Phase 6 style) - try multiple field names
        market_expiry = (
            market_data.get("close_time")
            or market_data.get("expiry")
            or market_data.get("expiration_time")
        )

    if not market_expiry:
        raise DataError("No expiry field found in market data")

    return market_expiry
