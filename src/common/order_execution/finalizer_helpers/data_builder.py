"""Data payload building for trade finalization"""

from typing import Any, Dict

from ...data_models.trading import OrderRequest, OrderResponse


def build_order_data_payload(
    order_request: OrderRequest, order_response: OrderResponse
) -> Dict[str, Any]:
    """
    Build order data payload for notification.

    Args:
        order_request: Original order request
        order_response: Order execution response

    Returns:
        Dictionary with order data for notification
    """
    filled_count = order_response.filled_count or 0
    remaining_count = order_response.remaining_count or 0
    initial_count = filled_count + remaining_count
    return {
        "ticker": order_request.ticker,
        "action": order_request.action.value,
        "side": order_request.side.value,
        "yes_price_cents": order_request.yes_price_cents,
        "count": initial_count,
        "client_order_id": order_response.client_order_id,
    }


def build_response_data_payload(order_response: OrderResponse) -> Dict[str, Any]:
    """
    Build response data payload for notification.

    Args:
        order_response: Order execution response

    Returns:
        Dictionary with response data for notification
    """
    status = getattr(order_response.status, "value", order_response.status)
    return {
        "order_id": order_response.order_id,
        "status": status,
        "filled_count": order_response.filled_count,
        "remaining_count": order_response.remaining_count,
        "average_fill_price_cents": order_response.average_fill_price_cents,
        "fees_cents": order_response.fees_cents,
    }
