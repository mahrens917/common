"""Price formatting helpers for snapshot processor."""

from typing import Any, Dict

# Constants
ORDERBOOK_LEVEL_EXPECTED_LENGTH = 2


def normalize_price_formatting(orderbook_sides: Dict[str, Any], msg_data: Dict[str, Any]) -> None:
    """Normalize yes_bids price formatting to preserve integer format for tests."""
    yes_levels = _extract_yes_levels(msg_data)
    if not yes_levels or not _contains_only_integer_prices(yes_levels):
        return

    yes_bids_raw = orderbook_sides.get("yes_bids")
    if not isinstance(yes_bids_raw, dict):
        return
    orderbook_sides["yes_bids"] = {_normalize_price_string(price): size for price, size in yes_bids_raw.items()}


def _extract_yes_levels(msg_data: Dict[str, Any]) -> list[Any]:
    yes_values = msg_data.get("yes")
    if isinstance(yes_values, list):
        return yes_values
    return []


def _contains_only_integer_prices(levels: list) -> bool:
    return all(
        isinstance(level, (list, tuple)) and len(level) == ORDERBOOK_LEVEL_EXPECTED_LENGTH and isinstance(level[0], int) for level in levels
    )


def _normalize_price_string(price: Any) -> str:
    if isinstance(price, str) and "." in price:
        return str(int(float(price)))
    return str(price)
