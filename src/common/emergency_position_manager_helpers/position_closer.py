"""Position closure execution for emergency management."""

import asyncio
import logging
import uuid
from typing import Optional, Tuple

from ..data_models.trading import (
    OrderAction,
    OrderRequest,
    OrderResponse,
    OrderType,
    PortfolioPosition,
    TimeInForce,
    TradeRule,
)
from ..kalshi_trading_client import KalshiTradingClient
from ..trading_exceptions import KalshiTradingError
from .order_completion_waiter import OrderCompletionWaiter

logger = logging.getLogger(__name__)

TRADING_OPERATION_ERRORS = (
    KalshiTradingError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)


class PositionCloser:
    """Executes emergency position closures."""

    def __init__(self, trading_client: KalshiTradingClient):
        self.trading_client = trading_client

    async def emergency_close_position(
        self, position: PortfolioPosition, reason: str = "Emergency closure"
    ) -> Tuple[bool, Optional[OrderResponse], str]:
        logger.warning("[PositionCloser] Emergency closing position %s: %s", position.ticker, reason)
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
            final_response = await self.trading_client.create_order_with_polling(close_request, timeout_seconds=10)
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

    async def _wait_for_order_completion(self, order_id: str, timeout_seconds: float = 30.0) -> Optional[OrderResponse]:
        return await OrderCompletionWaiter.wait_for_order_completion(order_id, self.trading_client, timeout_seconds)
