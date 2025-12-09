"""Position closure execution for emergency management."""

import asyncio
import logging
import uuid
from typing import Any, Optional, Tuple

from ..data_models.trading import (
    OrderAction,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    OrderType,
    PortfolioPosition,
    TimeInForce,
    TradeRule,
)
from ..kalshi_trading_client import KalshiTradingClient
from ..redis_protocol.typing import ensure_awaitable
from ..trading_exceptions import KalshiTradingError

logger = logging.getLogger(__name__)

TRADING_OPERATION_ERRORS = (
    KalshiTradingError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)

ORDER_POLLING_ERRORS = TRADING_OPERATION_ERRORS + (ValueError,)


class PositionCloser:
    """Executes emergency position closures."""

    def __init__(self, trading_client: KalshiTradingClient):
        self.trading_client = trading_client

    async def emergency_close_position(
        self, position: PortfolioPosition, reason: str = "Emergency closure"
    ) -> Tuple[bool, Optional[OrderResponse], str]:
        logger.warning(
            "[PositionCloser] Emergency closing position %s: %s", position.ticker, reason
        )
        try:
            position_side = position.side
            if position_side is None:
                raise ValueError("Position side must be specified for emergency closure")

            position_count = position.position_count
            if position_count is None:
                raise ValueError("Position count must be specified for emergency closure")

            close_request = OrderRequest(
                ticker=position.ticker,
                action=OrderAction.SELL,
                side=position_side,
                count=abs(position_count),
                client_order_id=str(uuid.uuid4()),
                trade_rule=TradeRule.EMERGENCY_EXIT.value,
                trade_reason=f"Emergency position closure: {reason}",
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL,
                yes_price_cents=0,
            )
            final_response = await self.trading_client.create_order_with_polling(
                close_request, timeout_seconds=10
            )
            filled_count = final_response.filled_count
            if filled_count is not None and filled_count > 0:
                logger.info(
                    "[PositionCloser] Successfully closed %s contracts of %s @ %s¢",
                    final_response.filled_count,
                    position.ticker,
                    final_response.average_fill_price_cents,
                )
                return True, final_response, "Position closed successfully"

            else:
                return False, final_response, "Order did not execute"
        except TRADING_OPERATION_ERRORS:
            logger.exception("[PositionCloser] Failed to close position %s", position.ticker)
            return False, None, "Closure failed"

    async def _wait_for_order_completion(
        self, order_id: str, timeout_seconds: float = 30.0
    ) -> Optional[OrderResponse]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds

        ensure_store = getattr(self.trading_client, "require_trade_store", None)
        if callable(ensure_store):
            await ensure_awaitable(ensure_store())

        while loop.time() < deadline:
            try:
                kalshi_client: Any = self.trading_client.kalshi_client
                fills = await kalshi_client.get_fills(order_id)
                if fills:
                    total_filled = self._count_fills(fills, order_id)
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

            except ORDER_POLLING_ERRORS:
                logger.warning("[PositionCloser] Error checking order %s", order_id)
                await asyncio.sleep(1.0)

        logger.warning(
            "[PositionCloser] Order %s did not complete within %ss", order_id, timeout_seconds
        )
        return None

    def _count_fills(self, fills, order_id: str) -> int:
        total_filled = 0
        for fill in fills:
            if "count" not in fill:
                logger.warning("[PositionCloser] Fill payload missing 'count': %s", fill)
                continue
            try:
                total_filled += int(fill["count"])
            except (TypeError, ValueError):
                logger.warning(
                    "[PositionCloser] Invalid fill count for %s: %s", order_id, fill["count"]
                )
        return total_filled
