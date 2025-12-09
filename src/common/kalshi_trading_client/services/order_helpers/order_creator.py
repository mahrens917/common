"""Order creation and metadata persistence."""

import logging
from typing import Any, Awaitable, Callable, NoReturn

from ....data_models.trading import OrderRequest, OrderResponse
from ....redis_protocol.trade_store import TradeStore, TradeStoreError
from ....trading_exceptions import (
    KalshiAPIError,
    KalshiTradePersistenceError,
    KalshiTradingError,
)
from ...constants import CLIENT_API_ERRORS

logger = logging.getLogger(__name__)

_FAILED_STORE_METADATA_ERROR = "Failed to store order metadata: {}"
_FAILED_CREATE_ORDER_ERROR = "Failed to create order"


class OrderCreator:
    """Handle order creation and immediate metadata persistence."""

    def __init__(
        self,
        kalshi_client,
        trade_store_getter: Callable[[], Awaitable[TradeStore]],
        notifier,
        metadata_resolver,
        validator,
    ):
        self._client = kalshi_client
        self.trade_store_getter = trade_store_getter
        self.notifier = notifier
        self.metadata_resolver = metadata_resolver
        self.validator = validator

    def set_notifier(self, notifier: Any) -> None:
        """Update the notifier used for order error reporting."""
        self.notifier = notifier

    async def create_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place an order and persist the associated metadata immediately."""
        return await _create_order(self, order_request)


async def _create_order(self, order_request: OrderRequest) -> OrderResponse:
    """
    Place an order and persist the associated metadata immediately.

    Returns:
        OrderResponse with order_id and initial status

    Raises:
        KalshiTradingError: For trading-specific errors
        KalshiAPIError: For general API errors
    """
    operation_name = "create_order"
    _log_order_submission(order_request, operation_name)

    try:
        self.validator.validate_order_request(order_request)

        order_response = await self._client.create_order(order_request)

        _log_order_result(order_response, operation_name)
        await _persist_order_metadata(self, order_request, order_response, operation_name)

    except KalshiTradingError as exc:
        await _notify_trading_error(self, order_request, exc, operation_name)
        raise
    except CLIENT_API_ERRORS + (ValueError, KeyError) as exc:
        await _handle_unexpected_order_error(self, order_request, exc, operation_name)
    else:
        return order_response


def _log_order_submission(order_request: OrderRequest, operation_name: str) -> None:
    logger.info(
        "[%s] Placing order: %s %s %s @ %s¢",
        operation_name,
        order_request.ticker,
        order_request.action.value,
        order_request.count,
        order_request.yes_price_cents,
    )


def _log_order_result(order_response: OrderResponse, operation_name: str) -> None:
    logger.info("[%s] Order placed successfully: %s", operation_name, order_response.order_id)
    logger.info(
        "[%s] Order status: %s, filled=%s, remaining=%s",
        operation_name,
        order_response.status.value,
        order_response.filled_count,
        order_response.remaining_count,
    )
    logger.info(
        "[%s] Trade metadata: rule=%s, reason=%s",
        operation_name,
        order_response.trade_rule,
        order_response.trade_reason,
    )


async def _persist_order_metadata(
    creator: OrderCreator,
    order_request: OrderRequest,
    order_response: OrderResponse,
    operation_name: str,
) -> None:
    try:
        market_category, metadata_station = creator.metadata_resolver.resolve_trade_context(
            order_request.ticker
        )
        trade_store = await creator.trade_store_getter()
        await trade_store.store_order_metadata(
            order_response.order_id,
            order_request.trade_rule,
            order_request.trade_reason,
            market_category=market_category,
            weather_station=metadata_station,
        )
        logger.debug("[%s] Stored order metadata for %s", operation_name, order_response.order_id)
    except TradeStoreError as metadata_error:
        raise KalshiTradePersistenceError(
            _FAILED_STORE_METADATA_ERROR.format(metadata_error),
            order_id=order_response.order_id,
            ticker=order_request.ticker,
            operation_name=operation_name,
        ) from metadata_error


async def _notify_trading_error(
    creator: OrderCreator,
    order_request: OrderRequest,
    exc: KalshiTradingError,
    operation_name: str,
) -> None:
    await creator.notifier.notify_order_error(
        order_request,
        exc,
        operation_name=operation_name,
        notifier_error_message="Failed to publish trading error notification",
    )


async def _handle_unexpected_order_error(
    creator: OrderCreator,
    order_request: OrderRequest,
    exc: Exception,
    operation_name: str,
) -> NoReturn:
    logger.exception(
        "[%s] Unexpected error (%s): %s",
        operation_name,
        type(exc).__name__,
        str(exc),
    )
    await creator.notifier.notify_order_error(
        order_request,
        exc,
        operation_name=operation_name,
        notifier_error_message="Failed to publish unexpected error notification",
    )
    raise KalshiAPIError(
        _FAILED_CREATE_ORDER_ERROR,
        operation_name=operation_name,
        response_data=order_request.__dict__,
    ) from exc
