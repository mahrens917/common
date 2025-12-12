"""Notification helpers for TradeFinalizer."""

import asyncio
import logging

from ...data_models.trading import OrderRequest, OrderResponse
from ...trading_exceptions import KalshiTradeNotificationError
from .data_builder import build_order_data_payload, build_response_data_payload

logger = logging.getLogger(__name__)


async def send_notification(
    notifier,
    order_request: OrderRequest,
    order_response: OrderResponse,
    order_id: str,
    kalshi_client,
    operation_name: str,
) -> None:
    """Send trade notification if notifier available."""
    if notifier is None:
        return

    order_data = build_order_data_payload(order_request, order_response)
    response_payload = build_response_data_payload(order_response)

    try:
        await notifier.send_order_executed_notification(order_data, response_payload, kalshi_client)
        logger.info("[%s] Trade notification dispatched for order %s", operation_name, order_id)
    except (RuntimeError, ConnectionError, TimeoutError, asyncio.TimeoutError, OSError) as exc:  # policy_guard: allow-silent-handler
        raise KalshiTradeNotificationError(
            f"Trade notification failed",
            order_id=order_id,
            operation_name=operation_name,
        ) from exc
