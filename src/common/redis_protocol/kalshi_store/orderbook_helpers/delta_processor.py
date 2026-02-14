"""
Delta processing for Kalshi orderbooks
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import orjson
from redis.asyncio import Redis

from ....market_filters.kalshi import extract_best_ask, extract_best_bid
from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from .best_price_updater import BestPriceUpdater
from .event_publisher import publish_market_event
from .field_converter import FieldConverter
from .side_data_updater import SideDataUpdater
from .snapshot_processor import SnapshotProcessor
from .snapshot_processor_helpers.redis_storage import store_optional_field

logger = logging.getLogger(__name__)


class DeltaProcessor(SnapshotProcessor):
    """Processes orderbook delta updates"""

    async def process_orderbook_delta(
        self,
        *,
        redis: Redis,
        market_key: str,
        market_ticker: str,
        msg_data: Dict[str, Any],
        timestamp: str,
    ) -> bool:
        parsed_inputs = _extract_delta_inputs(msg_data)
        if parsed_inputs is None:
            _none_guard_value = False
            return _none_guard_value

        side_field, price_str, delta = parsed_inputs
        side_data = await _apply_side_delta(redis, market_key, market_ticker, side_field, price_str, delta)
        if side_data is None:
            _none_guard_value = False
            return _none_guard_value

        await _update_top_of_book(self, redis, market_key, side_field, side_data)
        await ensure_awaitable(redis.hset(market_key, "timestamp", timestamp))
        await _update_trade_price_cache(self, redis, market_key, market_ticker)
        await publish_market_event(redis, market_key, market_ticker, timestamp)
        return True


def _extract_delta_inputs(msg_data: Dict[str, Any]) -> tuple[str, str, float] | None:
    """Validate incoming delta payload and return side field, price string, and delta."""
    side = FieldConverter.string_or_default(msg_data.get("side")).lower()
    price = msg_data.get("price")
    delta = msg_data.get("delta")

    if None in (side, price, delta):
        logger.error("Invalid delta message structure: %s", orjson.dumps(msg_data).decode())
        return None

    if not isinstance(price, (int, float)) or not isinstance(delta, (int, float)):
        logger.error(
            "Invalid numeric types in delta message: price=%r (type=%s), delta=%r (type=%s)",
            price,
            type(price),
            delta,
            type(delta),
        )
        return None

    resolved = _resolve_side_field(side, price)
    if resolved is None:
        logger.error("Unknown side in delta message: %s", side)
        return None

    side_field, price_str = resolved
    return side_field, price_str, float(delta)


def _resolve_side_field(side: str, price: float) -> tuple[str, str] | None:
    """Return the Redis field and price representation for the provided side."""
    if side == "yes":
        return "yes_bids", f"{float(price):.1f}"
    if side == "no":
        return "yes_asks", f"{100 - float(price):.1f}"
    return None


async def _apply_side_delta(
    redis: Redis,
    market_key: str,
    market_ticker: str,
    side_field: str,
    price_str: str,
    delta: float,
) -> dict | None:
    """Load the current side snapshot, apply the delta, and persist the result.

    Safe without transactions because message processing is sequential
    within the asyncio event loop (single consumer from the message queue).
    """
    try:
        side_json = await ensure_awaitable(redis.hget(market_key, side_field))
    except REDIS_ERRORS as exc:
        logger.error("Redis error retrieving %s for %s: %s", side_field, market_key, exc, exc_info=True)
        raise

    side_data = SideDataUpdater.apply_delta(SideDataUpdater.parse_side_data(side_json), price_str, delta)
    logger.debug("MARKET_UPDATE: Ticker=%s, Fields=['%s']", market_ticker, side_field)
    await ensure_awaitable(redis.hset(market_key, side_field, orjson.dumps(side_data).decode()))
    return side_data


async def _update_top_of_book(
    processor: DeltaProcessor,
    redis: Redis,
    market_key: str,
    side_field: str,
    side_data: dict,
) -> None:
    """Update the best bid/ask and sizes depending on the side that changed."""
    store_optional = getattr(processor, "_store_optional_field", None)
    if store_optional is None:
        store_optional = getattr(processor, "store_optional_field", store_optional_field)
    if side_field == "yes_bids":
        best_price, best_size = extract_best_bid(side_data)
        await store_optional(redis, market_key, "yes_bid", best_price)
        await store_optional(redis, market_key, "yes_bid_size", best_size)
    else:
        best_price, best_size = extract_best_ask(side_data)
        await store_optional(redis, market_key, "yes_ask", best_price)
        await store_optional(redis, market_key, "yes_ask_size", best_size)

    await BestPriceUpdater._recompute_direction(redis, market_key)


async def _update_trade_price_cache(processor: DeltaProcessor, redis: Redis, market_key: str, market_ticker: str) -> None:
    """Update cached trade prices when both bid/ask values are available."""
    yes_bid_raw = await ensure_awaitable(redis.hget(market_key, "yes_bid"))
    yes_ask_raw = await ensure_awaitable(redis.hget(market_key, "yes_ask"))
    decoded_yes_bid = yes_bid_raw.decode("utf-8", "ignore") if isinstance(yes_bid_raw, bytes) else yes_bid_raw
    decoded_yes_ask = yes_ask_raw.decode("utf-8", "ignore") if isinstance(yes_ask_raw, bytes) else yes_ask_raw
    parsed_yes_bid = FieldConverter.convert_numeric_field(decoded_yes_bid)
    parsed_yes_ask = FieldConverter.convert_numeric_field(decoded_yes_ask)
    if parsed_yes_bid is not None and parsed_yes_ask is not None:
        callback = processor.get_update_callback()
        await callback(market_ticker, parsed_yes_bid, parsed_yes_ask)
