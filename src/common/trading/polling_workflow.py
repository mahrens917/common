from __future__ import annotations

"""Reusable orchestration helpers for order polling and cancellation."""


import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Protocol

from ..data_models.trading import OrderResponse, OrderStatus
from ..order_execution import PollingOutcome
from ..trading_exceptions import KalshiOrderPollingError


class OrderPollerProtocol(Protocol):
    async def poll(self, order_id: str, timeout_seconds: float) -> Optional[PollingOutcome]: ...


CancelOrderFn = Callable[[str], Awaitable[bool]]
FetchOrderFn = Callable[[str], Awaitable[OrderResponse]]


@dataclass(frozen=True)
class PollingResult:
    """Result of the polling workflow."""

    order: OrderResponse
    outcome: Optional[PollingOutcome]
    was_cancelled: bool


class PollingWorkflow:
    """Drive post-order polling with optional cancellation on timeout."""

    def __init__(
        self,
        *,
        poller: OrderPollerProtocol,
        cancel_order: CancelOrderFn,
        fetch_order: FetchOrderFn,
        logger: logging.Logger,
    ) -> None:
        self._poller = poller
        self._cancel_order = cancel_order
        self._fetch_order = fetch_order
        self._logger = logger

    async def execute(
        self,
        *,
        order: OrderResponse,
        timeout_seconds: int,
        operation_name: str,
    ) -> PollingResult:
        """Poll for fills and cancel the order if it remains pending."""

        polling_outcome = await self._poller.poll(order.order_id, timeout_seconds)
        if polling_outcome is None:
            self._logger.info(
                "[%s] Order %s not filled after %ss timeout; attempting manual cancellation",
                operation_name,
                order.order_id,
                timeout_seconds,
            )

            cancelled = await self._cancel_order(order.order_id)
            if not cancelled:
                self._logger.error(
                    "[%s] Manual cancellation reported no success for order %s",
                    operation_name,
                    order.order_id,
                )
                raise KalshiOrderPollingError(
                    "Order polling timed out and cancellation returned no success indicator",
                    order_id=order.order_id,
                    operation_name=operation_name,
                )

            final_state = await self._fetch_order(order.order_id)
            if final_state.status != OrderStatus.CANCELLED:
                self._logger.error(
                    "[%s] Order %s expected to be cancelled but is %s",
                    operation_name,
                    order.order_id,
                    final_state.status.value,
                )
                raise KalshiOrderPollingError(
                    f"Order polling timeout cancellation yielded unexpected status {final_state.status.value}",
                    order_id=order.order_id,
                    operation_name=operation_name,
                )

            self._logger.info(
                "[%s] Order %s cancelled after polling timeout", operation_name, order.order_id
            )
            return PollingResult(order=final_state, outcome=None, was_cancelled=True)

        return PollingResult(order=order, outcome=polling_outcome, was_cancelled=False)


__all__ = ["PollingResult", "PollingWorkflow"]
