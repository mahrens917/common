"""Common utilities for orderbook parsing and manipulation."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import orjson

logger = logging.getLogger(__name__)


def parse_orderbook_field(
    market_data: Dict[str, Any], field_name: str, ticker: str
) -> Tuple[Optional[Dict[str, int]], Optional[str]]:
    """
    Parse orderbook JSON field from market data.

    Args:
        market_data: Market data dictionary
        field_name: Name of the field to parse (e.g., "yes_bids", "yes_asks")
        ticker: Market ticker for logging

    Returns:
        Tuple of (orderbook_dict, skip_reason)
        - If successful: (dict, None)
        - If failed: (None, skip_reason_string)
    """
    from common.parsing_utils import safe_json_loads

    field_value = market_data.get(field_name)
    field_json = field_value if isinstance(field_value, str) else "{}"

    if not field_json:
        return {}, None

    try:
        field_dict = safe_json_loads(field_json)
    except (ValueError, Exception):
        logger.exception(f"Failed to parse {field_name} JSON for {ticker}")
        return None, "INVALID_PRICE_DATA"

    if not isinstance(field_dict, dict) or (
        field_dict == {} and field_json and field_json not in ("{}", "")
    ):
        logger.error("Invalid orderbook JSON payload for %s %s", ticker, field_name)
        return None, "INVALID_PRICE_DATA"

    return field_dict, None


def parse_orderbook_levels(
    order_book_dict: Dict[str, int], is_buy_order: bool
) -> Optional[List[Tuple[float, int]]]:
    """
    Parse and sort orderbook levels.

    Args:
        order_book_dict: Dictionary of {price: size}
        is_buy_order: True for BUY orders (sort descending), False for SELL orders (sort ascending)

    Returns:
        Sorted list of (price, size) tuples or None if parsing fails
    """
    try:
        price_levels = [(float(price), int(size)) for price, size in order_book_dict.items()]
        price_levels.sort(key=lambda x: x[0], reverse=not is_buy_order)
    except (ValueError, TypeError):
        logger.exception("Invalid order book data types in dict")
        return None
    else:
        return price_levels


def extract_best_price_from_json(
    order_book_json: str, is_bid: bool
) -> Tuple[Optional[float], Optional[int]]:
    """
    Extract best price and size from orderbook JSON string.

    Args:
        order_book_json: JSON string containing orderbook data
        is_bid: True for bid side (highest price), False for ask side (lowest price)

    Returns:
        Tuple of (best_price, best_size) or (None, None) if parsing fails
    """
    if not order_book_json or order_book_json.strip() == "{}":
        return None, None

    try:
        order_book = orjson.loads(order_book_json)
        if not order_book:
            return None, None

        price_size_pairs = [(float(price), int(size)) for price, size in order_book.items()]

        if is_bid:
            best_price, best_size = max(price_size_pairs, key=lambda x: x[0])
        else:
            best_price, best_size = min(price_size_pairs, key=lambda x: x[0])
    except (orjson.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning(f"Failed to extract best price from orderbook JSON: {exc}")
        return None, None
    else:
        return best_price, best_size


def _get_default_price_result(allow_zero: bool) -> Tuple[Optional[float], Optional[int]]:
    """Return default result for empty or invalid orderbooks."""
    return (0.0, 0) if allow_zero else (None, None)


def _parse_price_size_pairs(order_book_dict: Dict[str, Any]) -> List[Tuple[float, int]]:
    """Parse orderbook dict to list of (price, size) tuples."""
    return [(float(price), int(size)) for price, size in order_book_dict.items()]


def _filter_valid_pairs(price_size_pairs: List[Tuple[float, int]]) -> List[Tuple[float, int]]:
    """Filter out pairs with zero or negative sizes."""
    return [(p, s) for p, s in price_size_pairs if s > 0]


def _select_best_price(valid_pairs: List[Tuple[float, int]], is_bid: bool) -> Tuple[float, int]:
    """Select best price from valid pairs based on side."""
    if is_bid:
        return max(valid_pairs, key=lambda x: x[0])
    return min(valid_pairs, key=lambda x: x[0])


def extract_best_price_from_dict(
    order_book_dict: Dict[str, Any], is_bid: bool, *, allow_zero: bool = False
) -> Tuple[Optional[float], Optional[int]]:
    """
    Extract best price and size from orderbook dictionary.

    Args:
        order_book_dict: Dictionary of {price: size}
        is_bid: True for bid side (highest price), False for ask side (lowest price)
        allow_zero: If True, return (0.0, 0) for empty orderbooks instead of (None, None)

    Returns:
        Tuple of (best_price, best_size) or (None, None) if parsing fails
        If allow_zero=True, returns (0.0, 0) for empty orderbooks
    """
    if not order_book_dict:
        return _get_default_price_result(allow_zero)

    try:
        price_size_pairs = _parse_price_size_pairs(order_book_dict)
        if not price_size_pairs:
            return _get_default_price_result(allow_zero)

        valid_pairs = _filter_valid_pairs(price_size_pairs)
        if not valid_pairs:
            return _get_default_price_result(allow_zero)

        return _select_best_price(valid_pairs, is_bid)
    except (ValueError, TypeError) as exc:
        logger.warning(f"Failed to extract best price from orderbook dict: {exc}")
        return _get_default_price_result(allow_zero)


def extract_best_bid_ask(orderbook: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract best bid and ask prices from full orderbook.

    Args:
        orderbook: Full orderbook dictionary with 'yes_bids' and 'yes_asks' fields

    Returns:
        Tuple of (best_bid_price, best_ask_price) or (None, None) if extraction fails
    """
    yes_bids = orderbook.get("yes_bids") or {}
    yes_asks = orderbook.get("yes_asks") or {}

    best_bid, _ = extract_best_price_from_dict(yes_bids, is_bid=True)
    best_ask, _ = extract_best_price_from_dict(yes_asks, is_bid=False)

    return best_bid, best_ask


def parse_and_extract_best_price(
    raw_order_book: Any, side: str, *, allow_zero: bool = False
) -> Tuple[Optional[float], Optional[int]]:
    """
    Parse raw orderbook data (dict or JSON string) and extract best price and size.

    This is a convenience function that handles both dict and JSON string inputs,
    making it suitable for parsing Kalshi market data where orderbooks may be in either format.

    Args:
        raw_order_book: Raw order book data (dict, string, or None)
        side: Order book side ("yes_bids" or "yes_asks")
        allow_zero: If True, return (0.0, 0) for empty orderbooks instead of (None, None)

    Returns:
        Tuple of (best_price, best_size)
        If allow_zero=True, returns (0.0, 0) for empty/invalid orderbooks
        Otherwise returns (None, None) for empty/invalid orderbooks

    Raises:
        ValueError: If JSON is invalid or data type is unexpected
        TypeError: If raw_order_book is not dict, str, or None
    """
    if raw_order_book in (None, "", "{}", {}):
        return (0.0, 0) if allow_zero else (None, None)

    if isinstance(raw_order_book, dict):
        order_book_dict = raw_order_book
    elif isinstance(raw_order_book, str):
        payload = raw_order_book.strip()
        if not payload:
            return (0.0, 0) if allow_zero else (None, None)
        try:
            order_book_dict = orjson.loads(payload)
        except orjson.JSONDecodeError as exc:
            raise ValueError(f"{side} field contains invalid JSON") from exc
        if not isinstance(order_book_dict, dict):
            raise TypeError(f"{side} field must decode to a JSON object")
    else:
        raise TypeError(f"{side} field must be a JSON object or string, got {type(raw_order_book)}")

    is_bid = side == "yes_bids"
    return extract_best_price_from_dict(order_book_dict, is_bid, allow_zero=allow_zero)
