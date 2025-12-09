"""
Orderbook parsing and size extraction helper.

This module provides Redis-specific orderbook parsing utilities that delegate to
canonical implementations in src.common.orderbook_utils for actual parsing logic.
"""

import logging
from typing import Any, Dict

from src.common.exceptions import DataError
from src.common.parsing_utils import safe_orjson_loads

logger = logging.getLogger(__name__)


def extract_orderbook_sizes(market_ticker: str, market_data: Dict[str, Any]) -> tuple[float, float]:
    """
    Extract best bid/ask sizes from a market snapshot orderbook.

    Delegates best-price resolution to src.common.orderbook_utils to ensure
    consistent parsing across Redis helpers.
    """
    orderbook_blob = market_data.get("orderbook")
    if orderbook_blob is None:
        raise DataError(f"Orderbook data missing for {market_ticker}")

    try:
        orderbook = safe_orjson_loads(orderbook_blob)
    except ValueError as exc:
        raise TypeError(f"Orderbook payload malformed for {market_ticker}") from exc
    if not isinstance(orderbook, dict):
        raise TypeError(f"Orderbook payload malformed for {market_ticker}")

    from src.common.orderbook_utils import extract_best_bid_ask

    best_bid_price, best_ask_price = extract_best_bid_ask(orderbook)
    if best_bid_price is None or best_ask_price is None:
        raise DataError(f"Orderbook data missing size information for {market_ticker}")

    yes_bids = orderbook.get("yes_bids") or {}
    yes_asks = orderbook.get("yes_asks") or {}
    return (
        resolve_orderbook_size(yes_bids, best_bid_price, market_ticker),
        resolve_orderbook_size(yes_asks, best_ask_price, market_ticker),
    )


def parse_orderbook_json(json_data: Any, field_name: str, ticker: str) -> Dict[str, Any]:
    """
    Parse orderbook JSON data from Redis.

    This is a thin wrapper around safe_orjson_loads() that handles Redis-specific
    patterns (None, bytes, empty strings). For more complex orderbook parsing,
    use functions from src.common.orderbook_utils.

    Args:
        json_data: JSON data to parse (may be None, bytes, or string)
        field_name: Field name for error messages
        ticker: Market ticker for error messages

    Returns:
        Parsed dictionary or empty dict on error
    """
    if not json_data:
        return {}

    try:
        parsed = safe_orjson_loads(json_data)
    except ValueError:
        logger.warning(f"Error parsing {field_name} for {ticker}")
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def resolve_orderbook_size(book: Dict[str, Any], price: float, market_ticker: str) -> float:
    """
    Resolve orderbook size for a given price level.

    Args:
        book: Orderbook dictionary {price: size}
        price: Price level to look up
        market_ticker: Market ticker for error messages

    Returns:
        Size at price level

    Raises:
        RuntimeError: If size cannot be resolved
    """
    key = str(price)
    if key not in book:
        key = format(price, "g")

    value = book.get(key)
    if value is None:
        raise RuntimeError(f"Orderbook entry missing size for price {price} in {market_ticker}")
    return float(value)


def extract_best_prices_from_orderbook(
    orderbook: Dict[str, Any], market_ticker: str
) -> tuple[float, float]:
    """
    Extract best bid and ask prices from orderbook.

    Delegates to canonical implementation in src.common.orderbook_utils.extract_best_bid_ask()
    with additional error handling for Kalshi store operations.

    Args:
        orderbook: Orderbook dictionary with 'yes_bids' and 'yes_asks' fields
        market_ticker: Market ticker for error messages

    Returns:
        Tuple of (best_bid_price, best_ask_price)

    Raises:
        DataError: If prices cannot be extracted
    """
    from src.common.orderbook_utils import extract_best_bid_ask

    best_bid, best_ask = extract_best_bid_ask(orderbook)

    if best_bid is None or best_ask is None:
        raise DataError(f"Orderbook data missing size information for {market_ticker}")

    return best_bid, best_ask
