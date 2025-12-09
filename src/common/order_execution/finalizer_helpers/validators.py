"""Validation helpers for TradeFinalizer."""

from ...data_models.trading import OrderRequest, OrderResponse
from ...trading_exceptions import KalshiTradePersistenceError


def validate_order_metadata(
    order_request: OrderRequest, order_id: str, ticker: str, operation_name: str
) -> None:
    """Validate that order request has required metadata."""
    trade_rule = getattr(order_request, "trade_rule", None)
    trade_reason = getattr(order_request, "trade_reason", None)

    if not trade_rule:
        raise KalshiTradePersistenceError(
            "Order request missing trade_rule metadata",
            order_id=order_id,
            ticker=ticker,
            operation_name=operation_name,
        )
    if not trade_reason:
        raise KalshiTradePersistenceError(
            "Order request missing trade_reason metadata",
            order_id=order_id,
            ticker=ticker,
            operation_name=operation_name,
        )


def validate_response_metadata(
    order_response: OrderResponse, order_id: str, ticker: str, operation_name: str
) -> None:
    """Validate that order response has required metadata."""
    if order_response.fees_cents is None:
        raise KalshiTradePersistenceError(
            "Order response missing fees_cents",
            order_id=order_id,
            ticker=ticker,
            operation_name=operation_name,
        )
