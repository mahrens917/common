"""Order polling coordination."""

import logging
from typing import TYPE_CHECKING, Awaitable, Callable

from ....data_models.trading import OrderRequest, OrderResponse, OrderStatus
from ....order_execution import PollingOutcome
from ....trading.polling_workflow import PollingWorkflow
from ....trading_exceptions import (
    KalshiOrderPollingError,
    KalshiTradeNotificationError,
    KalshiTradePersistenceError,
)
from .order_poller_helpers import apply_polling_outcome

if TYPE_CHECKING:
    from ....order_execution import OrderPoller, TradeFinalizer

logger = logging.getLogger(__name__)
_MISSING_FIELD = object()


class OrderPollerCoordinator:
    """Coordinate order polling and finalization."""

    def __init__(self, kalshi_client, poller_factory, finalizer_factory):
        self._client = kalshi_client
        self._poller_factory = poller_factory
        self._finalizer_factory = finalizer_factory

    async def complete_order_with_polling(
        self,
        order_request: OrderRequest,
        order_response: OrderResponse,
        timeout_seconds: int,
        cancel_order: Callable[[str], Awaitable[bool]],
    ) -> OrderResponse:
        """Poll for fills and finalise trade persistence after order placement."""
        return await _complete_order_with_polling(self, order_request, order_response, timeout_seconds, cancel_order)

    def apply_polling_outcome(self, order_response: OrderResponse, outcome: PollingOutcome) -> None:
        """Apply polling outcome to tracked order response."""
        apply_polling_outcome(order_response, outcome)

    @property
    def poller_factory(self) -> "Callable[[], OrderPoller]":
        return self._poller_factory

    @property
    def finalizer_factory(self) -> "Callable[[], TradeFinalizer]":
        return self._finalizer_factory


async def _complete_order_with_polling(
    self,
    order_request: OrderRequest,
    order_response: OrderResponse,
    timeout_seconds: int,
    cancel_order: Callable[[str], Awaitable[bool]],
) -> OrderResponse:
    """
    Poll for fills and finalise trade persistence after order placement.

    Returns:
        Final order response after polling completes
    """
    operation_name = "create_order_with_polling"
    _log_polling_submission(order_request, timeout_seconds, operation_name)

    short_circuit = _maybe_short_circuit_polling(order_response, operation_name)
    if short_circuit is not None:
        return short_circuit

    workflow = _build_polling_workflow(self, cancel_order, order_response)
    polling_result = await _execute_polling_workflow(workflow, order_response, timeout_seconds, operation_name)
    if polling_result.outcome is None:
        return polling_result.order

    order_after_polling = polling_result.order
    outcome = polling_result.outcome
    apply_polling_outcome(order_after_polling, outcome)
    _log_polling_fill(order_after_polling, outcome, operation_name)
    await _finalize_polled_trade(self, order_request, order_after_polling, outcome, operation_name)
    return order_after_polling


def _log_polling_submission(order_request: OrderRequest, timeout_seconds: int, operation_name: str):
    logger.info(
        "[%s] Placing GTC order with %ss timeout: %s %s %s @ %s¢",
        operation_name,
        timeout_seconds,
        order_request.ticker,
        order_request.action.value,
        order_request.count,
        order_request.yes_price_cents,
    )


def _maybe_short_circuit_polling(order_response: OrderResponse, operation_name: str):
    filled_count = getattr(order_response, "filled_count", _MISSING_FIELD)
    if filled_count is _MISSING_FIELD:
        filled_count = 0
    if isinstance(filled_count, int) and filled_count > 0:
        logger.info(
            "[%s] Order %s filled immediately: filled=%s",
            operation_name,
            order_response.order_id,
            filled_count,
        )
        return order_response
    if order_response.status == OrderStatus.CANCELLED:
        logger.info("[%s] Order %s cancelled immediately", operation_name, order_response.order_id)
        return order_response
    return None


def _build_polling_workflow(self, cancel_order, order_response: OrderResponse) -> PollingWorkflow:
    async def fetch_latest(order_id: str) -> OrderResponse:
        return await self._client.get_order(
            order_id,
            trade_rule=order_response.trade_rule,
            trade_reason=order_response.trade_reason,
        )

    poller = self._poller_factory()
    return PollingWorkflow(
        poller=poller,
        cancel_order=cancel_order,
        fetch_order=fetch_latest,
        logger=logger,
    )


async def _execute_polling_workflow(
    workflow: PollingWorkflow,
    order_response: OrderResponse,
    timeout_seconds: int,
    operation_name: str,
):
    try:
        return await workflow.execute(
            order=order_response,
            timeout_seconds=timeout_seconds,
            operation_name=operation_name,
        )
    except KalshiOrderPollingError:
        logger.exception("[%s] Polling failed for order %s", operation_name, order_response.order_id)
        raise


def _log_polling_fill(order_after_polling: OrderResponse, outcome: PollingOutcome, operation_name: str):
    logger.info(
        "[%s] Order %s filled after polling: filled=%s avg_price=%s¢",
        operation_name,
        order_after_polling.order_id,
        outcome.total_filled,
        outcome.average_price_cents,
    )


async def _finalize_polled_trade(
    self,
    order_request: OrderRequest,
    order_after_polling: OrderResponse,
    outcome: PollingOutcome,
    operation_name: str,
) -> None:
    trade_finalizer = self._finalizer_factory()
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
