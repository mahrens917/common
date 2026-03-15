"""
Snapshot processing for Kalshi orderbooks
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict

import orjson
from redis.asyncio import Redis

from ....market_filters.kalshi import extract_best_ask, extract_best_bid
from ...orderbook_utils import build_snapshot_sides
from ...streams.constants import EXCHANGE_EVENT_STREAM
from ...streams.publisher import stream_publish
from ...typing import ensure_awaitable
from ..utils_coercion import coerce_mapping as _canonical_coerce_mapping
from .best_price_updater import BestPriceUpdater
from .event_publisher import publish_market_event
from .snapshot_processor_helpers.redis_storage import build_hash_data, normalize_price_formatting

if TYPE_CHECKING:
    from .orderbook_cache import OrderbookCache

logger = logging.getLogger(__name__)


class SnapshotProcessor:
    """Processes orderbook snapshot updates"""

    def __init__(self, update_trade_prices_callback: Any):
        self._update_trade_prices_callback = update_trade_prices_callback
        self._cache: OrderbookCache | None = None

    def set_cache(self, cache: OrderbookCache) -> None:
        """Attach the in-memory cache for orderbook tracking."""
        self._cache = cache

    def get_update_callback(self) -> Any:
        """Return the callback responsible for publishing trade prices."""
        return self._update_trade_prices_callback

    def _extract_best_prices(self, orderbook_sides: Dict[str, Any]) -> tuple[Any, Any, Any, Any]:
        """Extract best bid/ask prices and sizes from orderbook."""
        yes_bids_payload = _canonical_coerce_mapping(orderbook_sides.get("yes_bids"))
        yes_asks_payload = _canonical_coerce_mapping(orderbook_sides.get("yes_asks"))
        yes_bid_price, yes_bid_size = extract_best_bid(yes_bids_payload)
        yes_ask_price, yes_ask_size = extract_best_ask(yes_asks_payload)
        return yes_bid_price, yes_ask_price, yes_bid_size, yes_ask_size

    def _build_combined_fields(
        self,
        hash_data: Dict[str, Any],
        timestamp: str,
        best_price_fields: list[tuple[str, Any]],
    ) -> Dict[str, Any]:
        """Merge hash data with timestamp and non-None price fields."""
        combined = {k: v for k, v in hash_data.items() if k != "timestamp"}
        combined["timestamp"] = timestamp
        for name, val in best_price_fields:
            if val is not None:
                combined[name] = str(val)
        return combined

    async def _write_to_redis(
        self,
        redis: Redis,
        market_key: str,
        market_ticker: str,
        timestamp: str,
        combined: Dict[str, Any],
        best_price_fields: list[tuple[str, Any]],
    ) -> None:
        """Write combined fields to Redis and publish update event."""
        await ensure_awaitable(redis.hset(market_key, mapping=combined))
        fields_to_del = [name for name, val in best_price_fields if val is None]
        if fields_to_del:
            await ensure_awaitable(redis.hdel(market_key, *fields_to_del))
        await asyncio.gather(
            BestPriceUpdater._recompute_direction(redis, market_key),
            publish_market_event(redis, market_key, market_ticker, timestamp),
        )

    async def process_orderbook_snapshot(
        self,
        *,
        redis: Redis,
        market_key: str,
        market_ticker: str,
        msg_data: Dict[str, Any],
        timestamp: str,
    ) -> bool:
        """Process orderbook snapshot message"""
        _has_levels = any(k in msg_data for k in ("yes", "no", "yes_dollars_fp", "no_dollars_fp"))
        if not _has_levels:
            logger.warning(
                "Kalshi snapshot for %s contains no orderbook levels; keeping existing Redis state",
                market_ticker,
            )
            return True

        orderbook_sides = build_snapshot_sides(msg_data, market_ticker)
        normalize_price_formatting(orderbook_sides, msg_data)
        hash_data = build_hash_data(orderbook_sides, timestamp)
        yes_bid_price, yes_ask_price, yes_bid_size, yes_ask_size = self._extract_best_prices(orderbook_sides)

        logger.info(
            "SNAPSHOT: ticker=%s yes_bid=%s yes_ask=%s yes_bid_size=%s yes_ask_size=%s",
            market_ticker,
            yes_bid_price,
            yes_ask_price,
            yes_bid_size,
            yes_ask_size,
        )

        best_price_fields = [
            ("yes_bid", yes_bid_price),
            ("yes_ask", yes_ask_price),
            ("yes_bid_size", yes_bid_size),
            ("yes_ask_size", yes_ask_size),
        ]
        combined = self._build_combined_fields(hash_data, timestamp, best_price_fields)

        if self._cache is not None:
            # Store side data as raw dicts so deltas skip JSON encode/decode.
            cache_fields = dict(combined)
            for side in ("yes_bids", "yes_asks"):
                if side in orderbook_sides:
                    cache_fields[side] = orderbook_sides[side]
            self._cache.store_snapshot(market_key, cache_fields)
            serialized = {k: orjson.dumps(v) if isinstance(v, dict) else v for k, v in cache_fields.items()}
            await ensure_awaitable(redis.hset(market_key, mapping=serialized))
            if self._cache.check_price_changed(market_key):
                await _publish_if_event(redis, self._cache, market_key, market_ticker, timestamp)
        else:
            await self._write_to_redis(redis, market_key, market_ticker, timestamp, combined, best_price_fields)

        callback = self.get_update_callback()
        await callback(market_ticker, yes_bid_price, yes_ask_price)
        return True


async def _publish_if_event(
    redis: Redis,
    cache: "OrderbookCache",
    market_key: str,
    market_ticker: str,
    timestamp: str,
) -> None:
    """Publish to exchange event stream if market has an event_ticker."""
    event_ticker = cache.get_event_ticker(market_key)
    if event_ticker is None:
        raw = await ensure_awaitable(redis.hget(market_key, "event_ticker"))
        if raw:
            event_ticker = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            cache.set_event_ticker(market_key, event_ticker)
    if event_ticker:
        await stream_publish(
            redis,
            EXCHANGE_EVENT_STREAM,
            {
                "event_ticker": event_ticker,
                "market_ticker": market_ticker,
                "timestamp": timestamp,
            },
        )
        cache.record_stream_publish()
