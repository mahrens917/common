"""ID normalization utilities for trade store."""

from typing import Any, List


def normalize_order_ids(raw_ids: Any) -> List[str]:
    """Normalize raw Redis order IDs to consistent string format."""
    order_ids: List[str] = []
    for order_id in raw_ids:
        if isinstance(order_id, bytes):
            order_ids.append(order_id.decode("utf-8"))
        else:
            order_ids.append(str(order_id))
    return order_ids
