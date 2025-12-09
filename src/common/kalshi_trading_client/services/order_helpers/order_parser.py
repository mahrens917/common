"""Order response parsing and validation."""

import logging
from typing import Any, Dict

from ....data_models.trading import OrderResponse
from ....trading_exceptions import KalshiDataIntegrityError

logger = logging.getLogger(__name__)


class OrderParser:
    """Parse and validate order responses."""

    @staticmethod
    def parse_order_response(
        response_data: Dict[str, Any], operation_name: str, trade_rule: str, trade_reason: str
    ) -> OrderResponse:
        """Strictly parse and validate a raw order response."""
        try:
            logger.info(f"[_parse_order_response] Parsing response: {response_data}")

            from ....order_response_parser import (
                parse_kalshi_order_response,
                validate_order_response_schema,
            )

            if "order" in response_data:
                order_data = validate_order_response_schema(response_data)
            else:
                order_data = response_data

            order_response = parse_kalshi_order_response(order_data, trade_rule, trade_reason)

            logger.info(
                f"[_parse_order_response] Successfully parsed order response for {order_response.order_id}"
            )
            logger.info(
                f"[_parse_order_response] Status: {order_response.status.value}, "
                f"Filled: {order_response.filled_count}, Remaining: {order_response.remaining_count}"
            )

        except ValueError as exc:
            raise KalshiDataIntegrityError(
                f"Order response validation failed: {exc}",
                operation_name=operation_name,
                data=response_data,
            ) from exc
        except (KeyError, TypeError, RuntimeError) as exc:
            raise KalshiDataIntegrityError(
                f"Unexpected error parsing order response: {exc}",
                operation_name=operation_name,
                data=response_data,
            ) from exc
        else:
            return order_response
