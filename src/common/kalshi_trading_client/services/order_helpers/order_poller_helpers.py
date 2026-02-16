"""Helper functions for OrderPollerCoordinator."""

import logging

from ....data_models.trading import OrderRequest, OrderResponse, OrderStatus
from ....order_execution import PollingOutcome
from ....trading.polling_workflow import PollingWorkflow
from ....trading_exceptions import (
    KalshiOrderPollingError,
    KalshiTradeNotificationError,
    KalshiTradePersistenceError,
)

logger = logging.getLogger(__name__)


def is_order_complete(operation_name: str, order_response: OrderResponse) -> bool:
    """Check if order is already filled or cancelled."""
    filled_count = order_response.filled_count
    if filled_count is None:
        filled_count = int()
    if filled_count > 0:
        logger.info(f"[{operation_name}] Order {order_response.order_id} filled immediately: " f"filled={order_response.filled_count}")
        return True

    if order_response.status == OrderStatus.CANCELLED:
        logger.info(f"[{operation_name}] Order {order_response.order_id} cancelled immediately")
        return True

    return False


def apply_polling_outcome(order_response: OrderResponse, outcome: PollingOutcome) -> None:
    """Apply polling outcome to order response."""
    filled_count = order_response.filled_count
    if filled_count is None:
        filled_count = int()
    remaining_count = order_response.remaining_count
    if remaining_count is None:
        remaining_count = int()
    initial_count = filled_count + remaining_count
    order_response.filled_count = outcome.total_filled
    order_response.remaining_count = max(0, initial_count - outcome.total_filled)
    order_response.average_fill_price_cents = outcome.average_price_cents
    remaining = max(0, initial_count - outcome.total_filled)
    if remaining > 0:
        order_response.status = OrderStatus.PARTIALLY_FILLED
    else:
        order_response.status = OrderStatus.FILLED


async def execute_polling_workflow(
    client,
    poller_factory,
    operation_name: str,
    order_response: OrderResponse,
    timeout_seconds: int,
    cancel_order,
):
    """Execute the polling workflow for order fills."""

    async def fetch_latest(order_id: str) -> OrderResponse:
        return await client.get_order(
            order_id,
            trade_rule=order_response.trade_rule,
            trade_reason=order_response.trade_reason,
        )

    poller = poller_factory()
    workflow = PollingWorkflow(
        poller=poller,
        cancel_order=cancel_order,
        fetch_order=fetch_latest,
        logger=logger,
    )

    try:
        return await workflow.execute(
            order=order_response,
            timeout_seconds=timeout_seconds,
            operation_name=operation_name,
        )
    except KalshiOrderPollingError:
        logger.exception(
            "[%s] Polling failed for order %s",
            operation_name,
            order_response.order_id,
        )
        raise


async def finalize_polling_result(
    finalizer_factory,
    operation_name: str,
    order_request: OrderRequest,
    polling_result,
) -> OrderResponse:
    """Apply outcome and finalize trade after polling."""
    order_after_polling = polling_result.order
    outcome = polling_result.outcome
    apply_polling_outcome(order_after_polling, outcome)
    logger.info(
        "[%s] Order %s filled after polling: filled=%s avg_price=%s¢",
        operation_name,
        order_after_polling.order_id,
        outcome.total_filled,
        outcome.average_price_cents,
    )

    trade_finalizer = finalizer_factory()

    try:
        await trade_finalizer.finalize(order_request, order_after_polling, outcome)
    except KalshiTradePersistenceError:
        logger.exception(
            "[%s] Trade persistence failed for order %s",
            operation_name,
            order_after_polling.order_id,
        )
        raise
    except KalshiTradeNotificationError:
        logger.exception(
            "[%s] Trade notification failed for order %s",
            operation_name,
            order_after_polling.order_id,
        )
        raise

    return order_after_polling
