"""Order request validation."""

import uuid

from ....data_models.trading import OrderRequest
from ....trading_exceptions import KalshiOrderValidationError

# Constants
_CONST_3 = 3


class OrderValidator:
    """Validate order requests before submission."""

    @staticmethod
    def validate_order_request(order_request: OrderRequest) -> None:
        """Verify order request payload meets trading requirements."""
        if not order_request.ticker or len(order_request.ticker) < _CONST_3:
            raise KalshiOrderValidationError(
                f"Invalid ticker format: {order_request.ticker}",
                operation_name="validate_order_request",
                order_data=order_request.__dict__,
            )

        try:
            uuid.UUID(order_request.client_order_id)
        except ValueError as exc:
            raise KalshiOrderValidationError(
                f"Client order ID must be valid UUID: {order_request.client_order_id}",
                operation_name="validate_order_request",
                order_data=order_request.__dict__,
            ) from exc

    @staticmethod
    def has_sufficient_balance_for_trade_with_fees(cached_balance_cents: int, trade_cost_cents: int, fees_cents: int) -> bool:
        """Determine whether cached balance covers trade cost and fees."""
        import logging

        logger = logging.getLogger(__name__)
        operation_name = "has_sufficient_balance_for_trade_with_fees"
        total_cost_cents = trade_cost_cents + fees_cents
        has_sufficient = cached_balance_cents >= total_cost_cents

        logger.info(
            f"[{operation_name}] Cached balance: {cached_balance_cents}¢ (${cached_balance_cents/100:.2f}), "
            f"Trade cost: {trade_cost_cents}¢, Fees: {fees_cents}¢, "
            f"Total: {total_cost_cents}¢ (${total_cost_cents/100:.2f}), "
            f"Sufficient: {has_sufficient}"
        )
        return has_sufficient
