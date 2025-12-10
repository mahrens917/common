"""Parse order fills from order response data."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from common.exceptions import DataError, ValidationError

from ..data_models.trading import OrderFill

logger = logging.getLogger(__name__)


def parse_fills_from_response(
    order_data: Dict[str, Any],
    timestamp: datetime,
    filled_count: int,
) -> List[OrderFill]:
    """
    Parse fills list from order response data.

    Args:
        order_data: Raw order data from Kalshi API
        timestamp: Order timestamp (fallback for fills without timestamp)
        filled_count: Expected total filled count

    Returns:
        List of OrderFill objects

    Raises:
        ValueError: If fills data is invalid or inconsistent
    """
    fills_data = order_data.get("fills")
    if not fills_data:
        return []

    fills: List[OrderFill] = []
    for fill_data in fills_data:
        fill = _parse_single_fill(fill_data, timestamp)
        fills.append(fill)

    _validate_total_fill_count(fills, filled_count)
    return fills


def _parse_single_fill(fill_data: Dict[str, Any], default_timestamp: datetime) -> OrderFill:
    """Parse a single fill entry."""
    _validate_fill_fields(fill_data)

    count_int = _extract_fill_count(fill_data)
    fill_timestamp = _extract_fill_timestamp(fill_data, default_timestamp)

    return OrderFill(
        price_cents=fill_data["price"],
        count=count_int,
        timestamp=fill_timestamp,
    )


def _validate_fill_fields(fill_data: Dict[str, Any]) -> None:
    """Validate required fields are present in fill data."""
    if "price" not in fill_data:
        raise DataError(f"Fill missing 'price' field: {fill_data}")
    if "count" not in fill_data:
        raise DataError(f"Fill missing 'count' field: {fill_data}")


def _extract_fill_count(fill_data: Dict[str, Any]) -> int:
    """Extract and validate fill count."""
    count_value = fill_data["count"]
    try:
        return int(count_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Invalid fill count value: {count_value}") from exc


def _extract_fill_timestamp(fill_data: Dict[str, Any], default_timestamp: datetime) -> datetime:
    """Extract fill timestamp or use default."""
    if "timestamp" not in fill_data:
        return default_timestamp

    try:
        return datetime.fromisoformat(str(fill_data["timestamp"]).replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValidationError(f"Invalid fill timestamp format: {fill_data['timestamp']}") from exc


def _validate_total_fill_count(fills: List[OrderFill], expected_count: int) -> None:
    """Validate total fill count matches expected."""
    total_fill_count = sum(fill.count for fill in fills)
    if total_fill_count != expected_count:
        raise ValueError(
            f"Fills count mismatch: sum of fills ({total_fill_count}) "
            f"doesn't match filled_count ({expected_count})"
        )
