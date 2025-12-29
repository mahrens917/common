"""
Snapshot processing for Kalshi orderbooks
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from redis.asyncio import Redis

from ....market_filters.kalshi import extract_best_ask, extract_best_bid
from ...orderbook_utils import build_snapshot_sides
from ...typing import ensure_awaitable
from ..utils_coercion import coerce_mapping as _canonical_coerce_mapping
from .snapshot_processor_helpers.price_formatting import normalize_price_formatting
from .snapshot_processor_helpers.redis_storage import (
    build_hash_data,
    store_best_prices,
    store_hash_fields,
)

logger = logging.getLogger(__name__)


class SnapshotProcessor:
    """Processes orderbook snapshot updates"""

    def __init__(self, update_trade_prices_callback: Any):
        """
        Initialize snapshot processor

        Args:
            update_trade_prices_callback: Callback to update trade prices (can be callable or object with method)
        """
        self._update_trade_prices_callback = update_trade_prices_callback

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
        if "yes" not in msg_data and "no" not in msg_data:
            logger.warning(
                "Kalshi snapshot for %s contains no orderbook levels; keeping existing Redis state",
                market_ticker,
            )
            return True

        orderbook_sides = build_snapshot_sides(msg_data, market_ticker)
        normalize_price_formatting(orderbook_sides, msg_data)
        hash_data = build_hash_data(orderbook_sides, timestamp)
        yes_bid_price, yes_ask_price, yes_bid_size, yes_ask_size = self._extract_best_prices(orderbook_sides)

        logger.debug(
            "MARKET_UPDATE: Ticker=%s, Fields=%s",
            market_ticker,
            list(hash_data.keys()),
        )

        await store_hash_fields(redis, market_key, hash_data, timestamp)
        await store_best_prices(redis, market_key, yes_bid_price, yes_ask_price, yes_bid_size, yes_ask_size)

        await _publish_market_event_update(redis, market_key, market_ticker, timestamp)

        callback = self.get_update_callback()
        await callback(market_ticker, yes_bid_price, yes_ask_price)
        return True


async def _publish_market_event_update(redis: Redis, market_key: str, market_ticker: str, timestamp: str) -> None:
    """Publish market event update for peak/extreme algo processing."""
    try:
        event_ticker = await ensure_awaitable(redis.hget(market_key, "event_ticker"))
        if event_ticker:
            if isinstance(event_ticker, bytes):
                event_ticker = event_ticker.decode("utf-8")
            channel = f"market_event_updates:{event_ticker}"
            payload = json.dumps({"market_ticker": market_ticker, "timestamp": timestamp})
            await redis.publish(channel, payload)
    except (RuntimeError, ConnectionError, OSError) as exc:  # policy_guard: allow-silent-handler
        logger.debug("Failed to publish market event update for %s: %s", market_ticker, exc)
