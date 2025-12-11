"""Extract and compute average fill price from order response."""

import logging
from typing import Any, Dict, Optional, TypeGuard

logger = logging.getLogger(__name__)


def extract_average_fill_price(order_data: Dict[str, Any], filled_count: int) -> Optional[int]:
    """
    Extract average fill price from order response.

    Args:
        order_data: Raw order data from Kalshi API
        filled_count: Number of filled contracts

    Returns:
        Average fill price in cents, or None if not available
    """
    if filled_count <= 0:
        return None

    _log_price_fields(order_data, filled_count)

    maker_cost = order_data.get("maker_fill_cost")
    if _is_valid_maker_cost(maker_cost):
        average = int(maker_cost) // filled_count
        logger.info("✅ [PRICE DEBUG] Using maker_fill_cost calculation: %s¢", average)
        return average

    _log_unreliable_price_warning(order_data)
    return None


def _log_price_fields(order_data: Dict[str, Any], filled_count: int) -> None:
    """Log all available price fields for debugging."""
    logger.info("🔍 [PRICE DEBUG] Raw order_data price fields:")

    maker_fill_cost = order_data.get("maker_fill_cost")
    yes_price = order_data.get("yes_price")
    no_price = order_data.get("no_price")
    side_value = order_data.get("side")

    logger.info("  maker_fill_cost: %s", maker_fill_cost)
    logger.info("  yes_price: %s", yes_price)
    logger.info("  no_price: %s", no_price)
    logger.info("  side: %s", side_value)
    logger.info("  filled_count: %s", filled_count)


def _is_valid_maker_cost(maker_cost: Any) -> TypeGuard[int | float]:
    """Check if maker_cost is valid and usable."""
    return isinstance(maker_cost, (int, float)) and maker_cost > 0


def _log_unreliable_price_warning(order_data: Dict[str, Any]) -> None:
    """Log warning about unreliable price data."""
    logger.warning("⚠️ [PRICE DEBUG] No reliable price in order status - setting to None (fills API will provide accurate price)")

    yes_price_log = order_data.get("yes_price")
    no_price_log = order_data.get("no_price")

    logger.warning(
        "   Order status yes_price: %s (UNRELIABLE - current market price)",
        yes_price_log,
    )
    logger.warning(
        "   Order status no_price: %s (UNRELIABLE - current market price)",
        no_price_log,
    )
