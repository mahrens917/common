"""Helper functions for delta processor complexity reduction."""

import logging
from typing import Any, Dict, Optional, Tuple

import orjson
from redis.asyncio import Redis

from ....market_filters.kalshi import extract_best_ask, extract_best_bid
from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from .field_converter import FieldConverter
from .side_data_updater import SideDataUpdater

logger = logging.getLogger(__name__)


def validate_delta_message(
    msg_data: Dict[str, Any],
) -> Tuple[bool, Optional[str], Optional[Any], Optional[Any]]:
    """
    Validate delta message structure and extract fields.

    Args:
        msg_data: Delta message data

    Returns:
        Tuple of (is_valid, side, price, delta)
    """
    side = FieldConverter.string_or_default(msg_data.get("side")).lower()
    price = msg_data.get("price")
    delta = msg_data.get("delta")

    if None in (side, price, delta):
        logger.error(
            "Invalid delta message structure: %s",
            orjson.dumps(msg_data).decode(),
        )
        return False, None, None, None

    if not isinstance(price, (int, float)) or not isinstance(delta, (int, float)):
        logger.error(
            "Invalid numeric types in delta message: price=%r (type=%s), delta=%r (type=%s)",
            price,
            type(price),
            delta,
            type(delta),
        )
        return False, None, None, None

    return True, side, price, delta


def determine_side_field_and_price(side: str, price: float) -> Tuple[Optional[str], Optional[str]]:
    """
    Determine Redis field name and price string based on side.

    Args:
        side: Order side ("yes" or "no")
        price: Price value

    Returns:
        Tuple of (side_field, price_str) or (None, None) if invalid
    """
    if side == "yes":
        return "yes_bids", str(price)
    elif side == "no":
        converted_price = 100 - float(price)
        return "yes_asks", str(converted_price)
    else:
        logger.error("Unknown side in delta message: %s", side)
        return None, None


async def apply_delta_to_orderbook(
    redis: Redis,
    market_key: str,
    side_field: str,
    price_str: str,
    delta: float,
) -> Dict[str, Any]:
    """
    Apply delta update to orderbook side data.

    Args:
        redis: Redis connection
        market_key: Market key
        side_field: Field name for side data
        price_str: Price string
        delta: Delta value

    Returns:
        Updated side data

    Raises:
        Redis errors are propagated
    """
    try:
        side_json = await ensure_awaitable(redis.hget(market_key, side_field))
    except REDIS_ERRORS as exc:
        logger.error("Redis error retrieving %s for %s: %s", side_field, market_key, exc, exc_info=True)
        raise

    side_data = SideDataUpdater.parse_side_data(side_json)
    return SideDataUpdater.apply_delta(side_data, price_str, delta)


async def update_best_prices(
    redis: Redis,
    market_key: str,
    side_field: str,
    side_data: Dict[str, Any],
    store_optional_field_func: Any,
) -> None:
    """
    Update best bid/ask prices based on side data.

    Args:
        redis: Redis connection
        market_key: Market key
        side_field: Field name indicating which side was updated
        side_data: Updated side data
        store_optional_field_func: Function to store optional fields
    """
    if side_field == "yes_bids":
        best_price, best_size = extract_best_bid(side_data)
        await store_optional_field_func(redis, market_key, "yes_bid", best_price)
        await store_optional_field_func(redis, market_key, "yes_bid_size", best_size)
    else:
        best_price, best_size = extract_best_ask(side_data)
        await store_optional_field_func(redis, market_key, "yes_ask", best_price)
        await store_optional_field_func(redis, market_key, "yes_ask_size", best_size)


async def extract_trade_prices(redis: Redis, market_key: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract yes_bid and yes_ask prices from Redis.

    Args:
        redis: Redis connection
        market_key: Market key

    Returns:
        Tuple of (yes_bid, yes_ask) or (None, None)
    """
    yes_bid_raw = await ensure_awaitable(redis.hget(market_key, "yes_bid"))
    yes_ask_raw = await ensure_awaitable(redis.hget(market_key, "yes_ask"))

    decoded_yes_bid = yes_bid_raw.decode("utf-8", "ignore") if isinstance(yes_bid_raw, bytes) else yes_bid_raw
    decoded_yes_ask = yes_ask_raw.decode("utf-8", "ignore") if isinstance(yes_ask_raw, bytes) else yes_ask_raw

    parsed_yes_bid = FieldConverter.convert_numeric_field(decoded_yes_bid)
    parsed_yes_ask = FieldConverter.convert_numeric_field(decoded_yes_ask)

    return parsed_yes_bid, parsed_yes_ask
