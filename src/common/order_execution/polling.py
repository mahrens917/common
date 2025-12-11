from __future__ import annotations

"""
Order polling helpers for the Kalshi trading client.

The poller orchestrates timeout handling and fill normalization so the caller can focus on
business-specific trade finalization logic.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..trading_exceptions import KalshiOrderPollingError
from .polling_helpers.fill_validator import (
    validate_fill_count,
    validate_fill_price,
    validate_fill_side,
)

logger = logging.getLogger(__name__)

FETCH_FILLS_ERRORS = (
    RuntimeError,
    ValueError,
    OSError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    KeyError,
    TypeError,
)

FillFetcher = Callable[[str], Awaitable[List[Dict[str, Any]]]]
Sleeper = Callable[[float], Awaitable[None]]


@dataclass(slots=True)
class PollingOutcome:
    """Aggregated fill information returned by the poller."""

    fills: List[Dict[str, Any]]
    total_filled: int
    average_price_cents: int


class OrderPoller:
    """
    Coordinates timeout waiting and fill retrieval for an order.

    The poller is intentionally stateless; callers should create fresh instances per request
    to avoid leaking dependencies between concurrent order executions.
    """

    def __init__(
        self,
        fetch_fills: FillFetcher,
        *,
        sleep: Optional[Sleeper] = None,
        operation_name: str = "create_order_with_polling",
    ) -> None:
        self._fetch_fills = fetch_fills
        self._sleep = sleep or asyncio.sleep
        self._operation_name = operation_name

    async def poll(self, order_id: str, timeout_seconds: float) -> Optional[PollingOutcome]:
        """
        Wait for the configured timeout and fetch fills once.

        Returns:
            PollingOutcome if fills were returned, otherwise None.

        Raises:
            KalshiOrderPollingError: When fill retrieval fails or invalid fills are returned.
        """
        await self._wait(timeout_seconds)
        fills = await self._retrieve_fills(order_id)
        if not fills:
            logger.info(
                "[%s] No fills returned for order %s after %.2fs timeout",
                self._operation_name,
                order_id,
                timeout_seconds,
            )
            return None

        outcome = self._summarize_fills(order_id, fills)
        logger.info(
            "[%s] Aggregated fills for order %s: filled=%s avg_price=%s¢",
            self._operation_name,
            order_id,
            outcome.total_filled,
            outcome.average_price_cents,
        )
        return outcome

    async def _wait(self, timeout_seconds: float) -> None:
        if timeout_seconds <= 0:
            return
        await self._sleep(timeout_seconds)

    async def _retrieve_fills(self, order_id: str) -> List[Dict[str, Any]]:
        try:
            return await self._fetch_fills(order_id)
        except FETCH_FILLS_ERRORS as exc:
            raise KalshiOrderPollingError(
                f"Failed to fetch fills: {exc}",
                order_id=order_id,
                operation_name=self._operation_name,
            ) from exc

    def _summarize_fills(self, order_id: str, fills: List[Dict[str, Any]]) -> PollingOutcome:
        total_filled = 0
        total_cost = 0

        for fill in fills:
            count = validate_fill_count(fill, order_id, self._operation_name)
            side = validate_fill_side(fill, order_id, self._operation_name)
            price_cents = validate_fill_price(fill, side, order_id, self._operation_name)

            total_filled += count
            total_cost += price_cents * count

        if total_filled <= 0:
            raise KalshiOrderPollingError(
                "Aggregated fill count is non-positive",
                order_id=order_id,
                operation_name=self._operation_name,
                request_data={"fills": fills},
            )

        average_price = total_cost // total_filled
        return PollingOutcome(fills=fills, total_filled=total_filled, average_price_cents=average_price)
