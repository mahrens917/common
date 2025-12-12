"""Order completion waiting logic for emergency position closures."""

import asyncio
import logging
from typing import Any, Optional

from ..data_models.trading import OrderStatus

logger = logging.getLogger(__name__)

ORDER_POLLING_ERRORS = (
    Exception,  # Broad catch for Kalshi errors
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    ValueError,
)


class OrderCompletionWaiter:
    """Waits for order completion and tracks fills."""

    @staticmethod
    async def wait_for_order_completion(
        order_id: str,
        trading_client: Any,
        timeout_seconds: float = 30.0,
    ) -> Optional[Any]:
        """Wait for order to complete."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds

        ensure_store = getattr(trading_client, "require_trade_store", None)
        if callable(ensure_store):
            from ..redis_protocol.typing import ensure_awaitable

            await ensure_awaitable(ensure_store())

        while loop.time() < deadline:
            try:
                kalshi_client: Any = trading_client.kalshi_client
                fills = await kalshi_client.get_fills(order_id)
                if fills:
                    total_filled = OrderCompletionWaiter._count_fills(fills, order_id)
                    if total_filled > 0:
                        logger.info(
                            "[PositionCloser] Emergency order %s filled: %s contracts",
                            order_id,
                            total_filled,
                        )

                order_response = await kalshi_client.get_order(order_id)
                if order_response and order_response.status in (
                    OrderStatus.FILLED,
                    OrderStatus.EXECUTED,
                    OrderStatus.CANCELLED,
                ):
                    return order_response

                await asyncio.sleep(0.5)

            except ORDER_POLLING_ERRORS:  # policy_guard: allow-silent-handler
                logger.warning("[PositionCloser] Error checking order %s", order_id)
                await asyncio.sleep(1.0)

        logger.warning("[PositionCloser] Order %s did not complete within %ss", order_id, timeout_seconds)
        return None

    @staticmethod
    def _count_fills(fills, order_id: str) -> int:
        """Count total fills from fills list."""
        total_filled = 0
        for fill in fills:
            if "count" not in fill:
                logger.warning("[PositionCloser] Fill payload missing 'count': %s", fill)
                continue
            try:
                total_filled += int(fill["count"])
            except (TypeError, ValueError):  # policy_guard: allow-silent-handler
                logger.warning("[PositionCloser] Invalid fill count for %s: %s", order_id, fill["count"])
        return total_filled
