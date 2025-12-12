"""Order cancellation handler."""

import importlib
import logging

from ....trading_exceptions import KalshiAPIError, KalshiOrderNotFoundError
from ...constants import CLIENT_API_ERRORS

logger = logging.getLogger(__name__)


class OrderCanceller:
    """Handle order cancellation via Kalshi API."""

    def __init__(self, kalshi_client):
        self._client = kalshi_client

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order via Kalshi's REST API.

        Returns:
            True if order was successfully cancelled
        """
        operation_name = "cancel_order"
        logger.info(f"[{operation_name}] Cancelling order: {order_id}")

        try:
            response_data = await self._client.api_request(
                method="DELETE",
                path=f"/trade-api/v2/portfolio/orders/{order_id}",
                params={},
                operation_name=operation_name,
            )

            validator = getattr(
                importlib.import_module("common.api_response_validators"),
                "validate_cancel_order_response",
            )

            try:
                validated_order = validator(response_data)
            except ValueError:  # policy_guard: allow-silent-handler
                logger.exception(f"[{operation_name}] Cancel response validation failed")
                logger.info(f"[{operation_name}] Raw response: {response_data}")
                raise

            status = validated_order["status"]
            if status in {"canceled", "cancelled"}:
                logger.info(f"[{operation_name}] Order {order_id} cancelled successfully")
                cancelled = True
            else:
                logger.error(f"[{operation_name}] Order {order_id} not canceled: status={validated_order['status']}")
                cancelled = False

        except CLIENT_API_ERRORS + (ValueError, KeyError) as exc:  # policy_guard: allow-silent-handler
            logger.exception(
                "[%s] Failed to cancel order %s (%s)",
                operation_name,
                order_id,
                type(exc).__name__,
            )
            if "not found" in str(exc).lower():
                raise KalshiOrderNotFoundError(
                    f"Order not found: {order_id}",
                    operation_name=operation_name,
                    order_id=order_id,
                ) from exc

            raise KalshiAPIError(
                f"Failed to cancel order",
                operation_name=operation_name,
                response_data={"order_id": order_id},
            ) from exc
        else:
            return cancelled
