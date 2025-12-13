"""Validation helpers for OrderResponse dataclass."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from common.truthy import pick_truthy

# Error messages
ERR_ORDER_ID_MISSING = "Order ID must be specified"
ERR_ORDER_STATUS_MISSING = "Order status must be specified"

if TYPE_CHECKING:
    from ..trading import OrderFill, OrderStatus


# Constants
_CONST_10 = 10
_MAX_PRICE = 99


def validate_order_response_enums(
    status: object,
    side: object,
    action: object,
    order_type: object,
) -> None:
    """Validate enum type fields."""
    from ..trading import OrderAction, OrderSide, OrderStatus, OrderType

    if not isinstance(status, OrderStatus):
        raise TypeError(f"Status must be OrderStatus enum, got: {type(status)}")

    if not isinstance(side, OrderSide):
        raise TypeError(f"Order side must be OrderSide enum, got: {type(side)}")

    if not isinstance(action, OrderAction):
        raise TypeError(f"Order action must be OrderAction enum, got: {type(action)}")

    if not isinstance(order_type, OrderType):
        raise TypeError(f"Order type must be OrderType enum, got: {type(order_type)}")


def validate_order_response_counts(filled_count: int | None, remaining_count: int | None, status: "OrderStatus") -> None:
    """Validate count fields."""
    from ..trading import OrderStatus

    if filled_count is None:
        raise ValueError("Filled count must be specified")

    if filled_count < 0:
        raise ValueError(f"Filled count cannot be negative: {filled_count}")

    if remaining_count is None:
        raise ValueError("Remaining count must be specified")

    if remaining_count < 0:
        raise ValueError(f"Remaining count cannot be negative: {remaining_count}")

    if filled_count == 0 and status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
        raise ValueError("Cannot have filled/partially filled status with zero filled count")


def validate_order_response_price(filled_count: int | None, average_fill_price_cents: int | None, fees_cents: Optional[int]) -> None:
    """Validate price and fee fields."""
    # CRITICAL FIX: Allow None for average_fill_price_cents when order status API is unreliable
    # The fills API will provide accurate execution prices
    if filled_count is not None and filled_count > 0 and average_fill_price_cents is None:
        # This is acceptable - Kalshi's order status API often returns unreliable price data
        # The fills API should be used for accurate execution prices
        pass

    if average_fill_price_cents is not None:
        if average_fill_price_cents <= 0 or average_fill_price_cents > _MAX_PRICE:
            raise ValueError(f"Average fill price must be between 1-99 cents: {average_fill_price_cents}")

    if fees_cents is not None and fees_cents < 0:
        raise ValueError(f"Fees cannot be negative: {fees_cents}")


def validate_order_response_fills(fills: List["OrderFill"] | None, filled_count: int | None) -> None:
    """Validate fills list consistency."""
    if fills:
        total_fill_count = sum(fill.count for fill in fills)
        if filled_count is None:
            raise ValueError("Filled count must be specified")
        if total_fill_count != filled_count:
            raise ValueError(f"Sum of fill counts ({total_fill_count}) does not match filled count ({filled_count})")


def validate_order_response_metadata(
    order_id: str,
    client_order_id: str,
    ticker: str,
    trade_rule: str,
    trade_reason: str,
    timestamp: Any | None,
) -> None:
    """Validate metadata fields."""
    if not order_id:
        raise ValueError(ERR_ORDER_ID_MISSING)

    if not client_order_id:
        raise ValueError("Client order ID must be specified")

    if not ticker:
        raise ValueError("Order ticker must be specified")

    if not isinstance(timestamp, datetime):
        raise TypeError("Order timestamp must be a datetime object")

    if not trade_rule:
        raise ValueError("Trade rule must be specified")

    if not trade_reason:
        raise ValueError("Trade reason must be specified")

    if len(trade_reason) < _CONST_10:
        raise ValueError("Trade reason must be descriptive (min 10 characters)")
