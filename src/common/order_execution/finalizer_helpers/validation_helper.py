"""Validation helper for trade finalizer."""

from ...data_models.trading import OrderRequest, OrderResponse
from ...trading_exceptions import KalshiTradePersistenceError


def validate_order_metadata(order_request: OrderRequest, order_response: OrderResponse, operation_name: str) -> None:
    """Validate required metadata is present."""
    ticker = order_request.ticker
    order_id = order_response.order_id

    if not getattr(order_request, "trade_rule", None):
        raise KalshiTradePersistenceError(
            "Order request missing trade_rule metadata",
            order_id=order_id,
            ticker=ticker,
            operation_name=operation_name,
        )
    if not getattr(order_request, "trade_reason", None):
        raise KalshiTradePersistenceError(
            "Order request missing trade_reason metadata",
            order_id=order_id,
            ticker=ticker,
            operation_name=operation_name,
        )
    if order_response.fees_cents is None:
        raise KalshiTradePersistenceError(
            "Order response missing fees_cents",
            order_id=order_id,
            ticker=ticker,
            operation_name=operation_name,
        )
