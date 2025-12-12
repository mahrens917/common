"""Helper functions for OrderCreator."""

import logging

from ....redis_protocol.trade_store import TradeStoreError
from ....trading_exceptions import (
    KalshiAPIError,
    KalshiTradePersistenceError,
)

logger = logging.getLogger(__name__)


async def store_order_metadata_safely(order_response, order_request, get_trade_store, metadata_resolver, operation_name: str):
    """Store order metadata with error handling."""
    try:
        market_category, metadata_station = metadata_resolver.resolve_trade_context(order_request.ticker)
        trade_store = await get_trade_store()
        await trade_store.store_order_metadata(
            order_response.order_id,
            order_request.trade_rule,
            order_request.trade_reason,
            market_category=market_category,
            weather_station=metadata_station,
        )
        logger.debug(f"[{operation_name}] Stored order metadata for {order_response.order_id}")
    except TradeStoreError as metadata_error:  # policy_guard: allow-silent-handler
        raise KalshiTradePersistenceError(
            f"Failed to store order metadata: {metadata_error}",
            order_id=order_response.order_id,
            ticker=order_request.ticker,
            operation_name=operation_name,
        ) from metadata_error


async def handle_order_error(notifier, order_request, exc, operation_name: str):
    """Handle order errors with notification."""
    await notifier.notify_order_error(
        order_request,
        exc,
        operation_name=operation_name,
        notifier_error_message="Failed to publish trading error notification",
    )


async def handle_unexpected_error(notifier, order_request, exc, operation_name: str):
    """Handle unexpected errors with logging and notification."""
    logger.error(
        "[%s] Unexpected error (%s): %s",
        operation_name,
        type(exc).__name__,
        str(exc),
    )

    await notifier.notify_order_error(
        order_request,
        exc,
        operation_name=operation_name,
        notifier_error_message="Failed to publish unexpected error notification",
    )

    raise KalshiAPIError(
        f"Failed to create order",
        operation_name=operation_name,
        response_data=order_request.__dict__,
    ) from exc
