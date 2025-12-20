"""
Orderbook Reader - Orderbook-specific read operations

Handles orderbook data retrieval, parsing, and size extraction.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from redis.asyncio import Redis

from common.truthy import pick_truthy

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from .orderbook_parser import (
    extract_orderbook_sizes,
    parse_orderbook_json,
)

logger = logging.getLogger(__name__)


class OrderbookReader:
    """Read orderbook data from Redis"""

    def __init__(self, logger_instance: logging.Logger):
        self.logger = logger_instance

    async def get_orderbook(self, redis: Redis, market_key: str, ticker: str) -> Dict:
        try:
            pipe = redis.pipeline()
            pipe.hget(market_key, "yes_bids")
            pipe.hget(market_key, "yes_asks")
            try:
                results = await pipe.execute()
            except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
                self.logger.error("Redis error fetching orderbook for %s: %s", ticker, exc, exc_info=True)
                return {}

            orderbook = {}
            for idx, field_name in enumerate(("yes_bids", "yes_asks")):
                parsed = parse_orderbook_json(results[idx], field_name, ticker)
                orderbook[field_name] = pick_truthy(parsed, {})

            else:
                return orderbook
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            self.logger.error("Redis error getting orderbook for %s: %s", ticker, exc, exc_info=True)
            return {}

    async def get_orderbook_side(self, redis: Redis, market_key: str, ticker: str, side: str) -> Dict:
        try:
            side_json = await ensure_awaitable(redis.hget(market_key, side))
            return parse_orderbook_json(side_json, side, ticker)
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            self.logger.error("Redis error getting %s for %s: %s", side, ticker, exc, exc_info=True)
            return {}

    @staticmethod
    def extract_orderbook_sizes(market_ticker: str, market_data: Dict[str, Any]) -> tuple[float, float]:
        return extract_orderbook_sizes(market_ticker, market_data)
