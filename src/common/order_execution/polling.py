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

from common.truthy import pick_if

from ..trading_exceptions_operational import KalshiOrderPollingError

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

_DEFAULT_POLL_INTERVAL_SECONDS = 0.5

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
        poll_interval: float = _DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> None:
        self._fetch_fills = fetch_fills
        self._sleep = sleep or asyncio.sleep
        self._operation_name = operation_name
        self._poll_interval = poll_interval

    async def poll(self, order_id: str, timeout_seconds: float) -> Optional[PollingOutcome]:
        """
        Poll for fills at regular intervals until timeout.

        Returns:
            PollingOutcome if fills were returned, otherwise None.

        Raises:
            KalshiOrderPollingError: When fill retrieval fails or invalid fills are returned.
        """
        elapsed = 0.0
        while elapsed < timeout_seconds:
            interval = min(self._poll_interval, timeout_seconds - elapsed)
            await self._wait(interval)
            elapsed += interval
            fills = await self._retrieve_fills(order_id)
            if fills:
                return self._build_outcome(order_id, fills)
        logger.info(
            "[%s] No fills returned for order %s after %.2fs timeout",
            self._operation_name,
            order_id,
            timeout_seconds,
        )
        return None

    def _build_outcome(self, order_id: str, fills: List[Dict[str, Any]]) -> PollingOutcome:
        outcome = self._summarize_fills(order_id, fills)
        logger.info(
            "[%s] Aggregated fills for order %s: filled=%s avg_price=%s¢",
            self._operation_name,
            order_id,
            outcome.total_filled,
            outcome.average_price_cents,
        )
        return outcome

    async def _wait(self, seconds: float) -> None:
        if seconds <= 0:
            return
        await self._sleep(seconds)

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

        average_price = round(total_cost / total_filled)
        return PollingOutcome(fills=fills, total_filled=total_filled, average_price_cents=average_price)


def validate_fill_count(fill: Dict[str, Any], order_id: str, operation_name: str) -> int:
    if "count" not in fill:
        raise KalshiOrderPollingError(
            "Fill missing 'count' value",
            order_id=order_id,
            operation_name=operation_name,
            request_data={"fill": fill},
        )

    try:
        count = int(fill["count"])
    except (TypeError, ValueError) as exc:
        raise KalshiOrderPollingError(
            f"Invalid fill count ({fill['count']})",
            order_id=order_id,
            operation_name=operation_name,
            request_data={"fill": fill},
        ) from exc

    if count <= 0:
        raise KalshiOrderPollingError(
            f"Received non-positive fill count ({count})",
            order_id=order_id,
            operation_name=operation_name,
            request_data={"fill": fill},
        )

    return count


def validate_fill_side(fill: Dict[str, Any], order_id: str, operation_name: str) -> str:
    if "side" not in fill:
        raise KalshiOrderPollingError(
            "Fill missing 'side'",
            order_id=order_id,
            operation_name=operation_name,
            request_data={"fill": fill},
        )

    side = fill["side"]
    if side not in ("yes", "no"):
        raise KalshiOrderPollingError(
            f"Fill missing valid side (received: {side})",
            order_id=order_id,
            operation_name=operation_name,
            request_data={"fill": fill},
        )

    return side


def validate_fill_price(fill: Dict[str, Any], side: str, order_id: str, operation_name: str) -> int:
    price_key = pick_if(side == "yes", lambda: "yes_price", lambda: "no_price")

    if price_key not in fill:
        raise KalshiOrderPollingError(
            f"Fill missing {price_key}",
            order_id=order_id,
            operation_name=operation_name,
            request_data={"fill": fill},
        )

    price = fill[price_key]
    try:
        return int(price)
    except (TypeError, ValueError) as exc:
        raise KalshiOrderPollingError(
            f"Invalid price in fill ({price})",
            order_id=order_id,
            operation_name=operation_name,
            request_data={"fill": fill},
        ) from exc
