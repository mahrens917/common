"""Fill validation logic for order polling"""

from typing import Any, Dict

from ...trading_exceptions import KalshiOrderPollingError


def validate_fill_count(fill: Dict[str, Any], order_id: str, operation_name: str) -> int:
    """
    Validate and extract fill count.

    Args:
        fill: Fill dictionary
        order_id: Order ID for error messages
        operation_name: Operation name for error messages

    Returns:
        Validated count as integer

    Raises:
        KalshiOrderPollingError: If count is invalid
    """
    if "count" not in fill:
        raise KalshiOrderPollingError(
            "Fill missing 'count' value",
            order_id=order_id,
            operation_name=operation_name,
            request_data={"fill": fill},
        )

    try:
        count = int(fill["count"])
    except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
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
    """
    Validate and extract fill side.

    Args:
        fill: Fill dictionary
        order_id: Order ID for error messages
        operation_name: Operation name for error messages

    Returns:
        Validated side ('yes' or 'no')

    Raises:
        KalshiOrderPollingError: If side is invalid
    """
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
    """
    Validate and extract fill price.

    Args:
        fill: Fill dictionary
        side: Side of fill ('yes' or 'no')
        order_id: Order ID for error messages
        operation_name: Operation name for error messages

    Returns:
        Validated price in cents

    Raises:
        KalshiOrderPollingError: If price is invalid
    """
    price_key = "yes_price" if side == "yes" else "no_price"

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
    except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
        raise KalshiOrderPollingError(
            f"Invalid price in fill ({price})",
            order_id=order_id,
            operation_name=operation_name,
            request_data={"fill": fill},
        ) from exc
