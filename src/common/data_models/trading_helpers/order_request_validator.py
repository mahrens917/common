"""Validation helpers for OrderRequest dataclass."""

from typing import TYPE_CHECKING

# Error messages
ERR_ORDER_QUANTITY_NOT_POSITIVE = "Order quantity must be positive: {value}"
ERR_ORDER_PRICE_NOT_POSITIVE = "Order price must be positive: {value}"


if TYPE_CHECKING:
    from ..trading import OrderType


# Constants
_CONST_10 = 10
_MAX_PRICE = 99


def validate_order_request_enums(
    action: object,
    side: object,
    order_type: object,
    time_in_force: object,
) -> None:
    """Validate enum type fields."""
    from ..trading import OrderAction, OrderSide, OrderType, TimeInForce

    if not isinstance(action, OrderAction):
        raise TypeError(f"Action must be OrderAction enum, got: {type(action)}")

    if not isinstance(side, OrderSide):
        raise TypeError(f"Side must be OrderSide enum, got: {type(side)}")

    if not isinstance(order_type, OrderType):
        raise TypeError(f"Order type must be OrderType enum, got: {type(order_type)}")

    if not isinstance(time_in_force, TimeInForce):
        raise TypeError(f"Time in force must be TimeInForce enum, got: {type(time_in_force)}")


def validate_order_request_price(order_type: "OrderType", yes_price_cents: int | None) -> None:
    """Validate price field based on order type."""
    from ..trading import OrderType

    if order_type == OrderType.LIMIT:
        if yes_price_cents is None:
            raise ValueError("Limit orders must specify yes_price_cents")
        if yes_price_cents <= 0 or yes_price_cents > _MAX_PRICE:
            raise ValueError(f"Yes price must be between 1-99 cents: {yes_price_cents}")
    elif order_type == OrderType.MARKET:
        if yes_price_cents is None:
            raise ValueError(
                "Market orders must specify yes_price_cents (use 0 for exchange default behaviour)"
            )
        if yes_price_cents < 0 or yes_price_cents > _MAX_PRICE:
            raise ValueError(f"Market order price must be between 0-99 cents: {yes_price_cents}")


def validate_order_request_metadata(
    ticker: str, count: int, client_order_id: str, trade_rule: str, trade_reason: str
) -> None:
    """Validate metadata fields."""
    if not ticker:
        raise ValueError("Ticker must be specified")

    if count <= 0:
        raise ValueError(f"Count must be positive: {count}")

    if not client_order_id:
        raise ValueError("Client order ID must be specified")

    if not trade_rule:
        raise ValueError("Trade rule must be specified")

    if not trade_reason:
        raise ValueError("Trade reason must be specified")

    if len(trade_reason) < _CONST_10:
        raise ValueError("Trade reason must be descriptive (min 10 characters)")
