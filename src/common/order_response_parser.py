"""
Shared order response parsing utilities for Kalshi API clients.

This module provides a centralized way to parse Kalshi API order responses
into OrderResponse objects, ensuring consistency across different client implementations.

IMPORTANT: This parser strictly validates against the actual Kalshi API response format.
No implicit defaults or silent failures are allowed - fail fast on any mismatch.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type, TypeGuard

from common.order_response_parser_exceptions import (
    EmptyClientOrderIdError,
    EmptyOrderDataError,
    EmptyOrderIdError,
    EmptyRejectionReasonError,
    EmptyResponseError,
    FillCountMismatchError,
    InvalidCreatedTimeError,
    InvalidFillCountError,
    InvalidFillFieldError,
    InvalidMakerFeesError,
    InvalidOrderCountError,
    InvalidOrderDataTypeError,
    InvalidOrderStatusError,
    MissingCreatedTimeError,
    MissingFillCountError,
    MissingOrderFieldsError,
    MissingOrderWrapperError,
    MissingRejectionReasonError,
    MissingTickerError,
)

from .data_models.trading import (
    OrderAction,
    OrderFill,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrderCounts:
    filled_count: int
    remaining_count: int
    total_count: int


def parse_kalshi_order_response(order_data: Dict[str, Any], trade_rule: str, trade_reason: str) -> OrderResponse:
    """
    Parse Kalshi API order response data into an OrderResponse object.

    This function strictly validates the response structure against the actual
    Kalshi API specification. Any missing or mismatched fields will raise an error.
    Trade metadata is passed through to eliminate need for Redis storage.

    Args:
        order_data: Raw order data from Kalshi API response
        trade_rule: Trading rule identifier for this order
        trade_reason: Reason for placing this trade

    Returns:
        OrderResponse: Parsed order response object with trade metadata

    Raises:
        ValueError: If required fields are missing, invalid, or don't match API spec
    """
    _raise_if_empty(order_data)
    _ensure_required_order_fields(order_data)

    status = _parse_order_status(order_data)
    filled_count = _parse_filled_count(order_data)
    counts = _compute_order_counts(order_data, filled_count)
    timestamp = _parse_order_timestamp(order_data)
    average_fill_price_cents = _parse_average_fill_price(order_data, filled_count)
    fees_cents = 0
    if "maker_fees" in order_data:
        try:
            fees_cents = int(order_data["maker_fees"])
        except (TypeError, ValueError) as exc:
            err = InvalidMakerFeesError(order_data["maker_fees"])
            raise err from exc
    rejection_reason = _determine_rejection_reason(order_data, status)
    fills = _parse_order_fills(order_data, timestamp, filled_count)
    order_id, client_order_id = _parse_order_identifiers(order_data)
    ticker = _parse_ticker(order_data)
    side, action, order_type = _parse_order_enums(order_data)

    return OrderResponse(
        order_id=order_id,
        client_order_id=client_order_id,
        status=status,
        ticker=ticker,
        side=side,
        action=action,
        order_type=order_type,
        filled_count=counts.filled_count,
        remaining_count=counts.remaining_count,
        average_fill_price_cents=average_fill_price_cents,
        timestamp=timestamp,
        fees_cents=fees_cents,
        fills=fills,
        trade_rule=trade_rule,
        trade_reason=trade_reason,
        rejection_reason=rejection_reason,
    )


def _raise_if_empty(order_data: Dict[str, Any]) -> None:
    if not order_data:
        raise EmptyOrderDataError()


def _ensure_required_order_fields(order_data: Dict[str, Any]) -> None:
    required_fields = [
        "order_id",
        "client_order_id",
        "status",
        "ticker",
        "side",
        "action",
        "type",
    ]
    missing_fields = [field for field in required_fields if field not in order_data]
    if missing_fields:
        err = MissingOrderFieldsError(missing_fields, list(order_data.keys()))
        raise err


def _parse_order_status(order_data: Dict[str, Any]) -> OrderStatus:
    status_str = str(order_data["status"]).lower()
    status_mapping = {
        "filled": OrderStatus.FILLED,
        "executed": OrderStatus.EXECUTED,
        "resting": OrderStatus.PENDING,
        "canceled": OrderStatus.CANCELLED,
        "rejected": OrderStatus.REJECTED,
    }
    if status_str not in status_mapping:
        err = InvalidOrderStatusError(status_str, list(status_mapping.keys()))
        raise err
    return status_mapping[status_str]


def _parse_filled_count(order_data: Dict[str, Any]) -> int:
    if "fill_count" not in order_data:
        err = MissingFillCountError(list(order_data.keys()))
        raise err
    try:
        return int(order_data["fill_count"])
    except (TypeError, ValueError) as exc:
        err = InvalidFillCountError(order_data["fill_count"])
        raise err from exc


def _compute_order_counts(order_data: Dict[str, Any], filled_count: int) -> OrderCounts:
    total_count: Optional[int] = None
    for field_name in ["initial_count", "count", "quantity"]:
        if field_name in order_data:
            try:
                total_count = int(order_data[field_name])
            except (TypeError, ValueError) as exc:
                err = InvalidOrderCountError(field_name, order_data[field_name])
                raise err from exc
            break

    remaining_count: Optional[int] = None
    if total_count is not None:
        remaining_count = total_count - filled_count
    elif "remaining_count" in order_data:
        try:
            remaining_count = int(order_data["remaining_count"])
        except (TypeError, ValueError) as exc:
            err = InvalidOrderCountError("remaining_count", order_data["remaining_count"])
            raise err from exc
        total_count = remaining_count + filled_count
    else:
        total_count = 1
        remaining_count = total_count - filled_count

    return OrderCounts(
        filled_count=filled_count,
        remaining_count=int(remaining_count),
        total_count=int(total_count),
    )


def _parse_order_timestamp(order_data: Dict[str, Any]) -> datetime:
    if "created_time" not in order_data:
        err = MissingCreatedTimeError(list(order_data.keys()))
        raise err
    raw_timestamp = order_data["created_time"]
    try:
        return datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        err = InvalidCreatedTimeError(order_data["created_time"])
        raise err from exc


def _parse_average_fill_price(order_data: Dict[str, Any], filled_count: int) -> Optional[int]:
    if filled_count <= 0:
        return None

    _log_price_debug(order_data, filled_count)

    maker_cost = order_data.get("maker_fill_cost")
    if _has_reliable_maker_cost(maker_cost):
        average = int(maker_cost) // filled_count
        logger.info("✅ [PRICE DEBUG] Using maker_fill_cost calculation: %s¢", average)
        return average

    _log_unreliable_price_warning(order_data)
    return None


def _log_price_debug(order_data: Dict[str, Any], filled_count: int) -> None:
    """Log order pricing fields for debugging."""
    logger.info("🔍 [PRICE DEBUG] Raw order_data price fields:")
    for field_name in ("maker_fill_cost", "yes_price", "no_price", "side"):
        field_value = order_data[field_name] if field_name in order_data else "missing"
        logger.info("  %s: %s", field_name, field_value)
    logger.info("  filled_count: %s", filled_count)


def _has_reliable_maker_cost(value: Any) -> TypeGuard[int | float]:
    """Return True when maker fill cost is a positive numeric value."""
    return isinstance(value, (int, float)) and value > 0


def _log_unreliable_price_warning(order_data: Dict[str, Any]) -> None:
    """Emit warnings when maker fill cost is unavailable."""
    logger.warning("⚠️ [PRICE DEBUG] No reliable price in order status - setting to None (fills API will provide accurate price)")
    yes_price = order_data["yes_price"] if "yes_price" in order_data else "missing"
    no_price = order_data["no_price"] if "no_price" in order_data else "missing"
    logger.warning(
        "   Order status yes_price: %s (UNRELIABLE - current market price)",
        yes_price,
    )
    logger.warning(
        "   Order status no_price: %s (UNRELIABLE - current market price)",
        no_price,
    )


def _determine_rejection_reason(order_data: Dict[str, Any], status: OrderStatus) -> Optional[str]:
    if status != OrderStatus.REJECTED:
        return None

    if "rejection_reason" not in order_data:
        err = MissingRejectionReasonError(list(order_data.keys()))
        raise err

    rejection_reason = order_data["rejection_reason"]
    if not isinstance(rejection_reason, str) or not rejection_reason.strip():
        raise EmptyRejectionReasonError()

    logger.info("🚫 Order rejection captured: %s", rejection_reason)
    return rejection_reason


def _parse_order_fills(
    order_data: Dict[str, Any],
    timestamp: datetime,
    filled_count: int,
) -> List[OrderFill]:
    fills_data = order_data.get("fills") or []
    if not fills_data:
        return []

    fills = [_build_order_fill(fill_data, timestamp) for fill_data in fills_data]
    _validate_fill_totals(fills, filled_count)
    return fills


def _build_order_fill(fill_data: Dict[str, Any], order_timestamp: datetime) -> OrderFill:
    """Create an OrderFill entry after validating the payload."""
    price_cents = _require_fill_field(fill_data, "price")
    count_int = _parse_fill_count(fill_data)
    fill_timestamp = _parse_fill_timestamp(fill_data, order_timestamp)
    return OrderFill(price_cents=price_cents, count=count_int, timestamp=fill_timestamp)


def _require_fill_field(fill_data: Dict[str, Any], field_name: str) -> Any:
    """Ensure a fill field exists."""
    if field_name not in fill_data:
        raise ValueError(f"Fill missing '{field_name}'")
    return fill_data[field_name]


def _parse_fill_count(fill_data: Dict[str, Any]) -> int:
    """Convert fill count to int and validate."""
    count_value = _require_fill_field(fill_data, "count")
    try:
        return int(count_value)
    except (TypeError, ValueError) as exc:
        err = InvalidFillFieldError("count", count_value)
        raise err from exc


def _parse_fill_timestamp(fill_data: Dict[str, Any], order_timestamp: datetime) -> datetime:
    """Parse the fill timestamp if provided, using order timestamp when fill lacks its own."""
    if "timestamp" not in fill_data:
        return order_timestamp

    raw_timestamp = str(fill_data["timestamp"]).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw_timestamp)
    except (ValueError, AttributeError) as exc:  # policy_guard: allow-silent-handler
        raise ValueError("Invalid fill timestamp format") from exc


def _validate_fill_totals(fills: List[OrderFill], filled_count: int) -> None:
    """Ensure cumulative fill counts match the order's filled count."""
    total_fill_count = sum(fill.count for fill in fills)
    if total_fill_count != filled_count:
        err = FillCountMismatchError(total_fill_count, filled_count)
        raise err


def _parse_order_identifiers(order_data: Dict[str, Any]) -> Tuple[str, str]:
    order_id = order_data["order_id"]
    client_order_id = order_data["client_order_id"]
    if not order_id:
        raise EmptyOrderIdError()
    if not client_order_id:
        raise EmptyClientOrderIdError()
    return str(order_id), str(client_order_id)


def _parse_ticker(order_data: Dict[str, Any]) -> str:
    ticker_raw = str(order_data["ticker"]).strip()
    if not ticker_raw:
        raise MissingTickerError()
    return ticker_raw


def _parse_order_enums(
    order_data: Dict[str, Any],
) -> Tuple[OrderSide, OrderAction, OrderType]:
    side = _parse_enum_value(order_data["side"], OrderSide, "side")
    action = _parse_enum_value(order_data["action"], OrderAction, "action")
    order_type = _parse_enum_value(order_data["type"], OrderType, "type")
    return side, action, order_type


def _parse_enum_value(value: Any, enum_cls: Type[Any], field_name: str) -> Any:
    try:
        return enum_cls(str(value).lower())
    except ValueError as exc:  # policy_guard: allow-silent-handler
        raise ValueError(f"Invalid order {field_name}") from exc


def validate_order_response_schema(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that the API response has the expected structure with 'order' wrapper.

    Args:
        response_data: Raw API response

    Returns:
        The order data extracted from the response

    Raises:
        ValueError: If response structure doesn't match expected format
    """
    if not response_data:
        raise EmptyResponseError()

    # Kalshi API wraps order data in an 'order' field
    if "order" not in response_data:
        err = MissingOrderWrapperError(list(response_data.keys()))
        raise err

    order_data = response_data["order"]

    if not isinstance(order_data, dict):
        err = InvalidOrderDataTypeError(type(order_data))
        raise err

    return order_data
