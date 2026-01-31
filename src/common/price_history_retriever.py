"""
Price history retrieval for history tracking

Handles fetching and parsing of price history from Redis sorted set with
time-range filtering via ZRANGEBYSCORE.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import List, Tuple

from common.price_history_utils import generate_redis_key, parse_history_member_value, validate_currency
from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.time_utils import get_current_utc

from .price_history_connection_manager import REDIS_ERRORS
from .price_history_parser import PriceHistoryParser

logger = logging.getLogger(__name__)


class PriceHistoryRetriever:
    """Retrieves price history from Redis sorted set."""

    def __init__(self):
        self._parser = PriceHistoryParser()

    async def get_history(self, client: RedisClient, currency: str, hours: int = 24) -> List[Tuple[int, float]]:
        """Retrieve history via ZRANGEBYSCORE for the requested time window."""
        return await _get_history(client, currency, hours)


def _calculate_start_timestamp(hours: int) -> float:
    current_time = get_current_utc()
    start_time = current_time - timedelta(hours=hours)
    return start_time.timestamp()


async def _get_history(client: RedisClient, currency: str, hours: int = 24) -> List[Tuple[int, float]]:
    validate_currency(currency)
    try:
        redis_key = generate_redis_key(currency)
        start_ts = _calculate_start_timestamp(hours)
        entries = await ensure_awaitable(client.zrangebyscore(redis_key, start_ts, "+inf", withscores=True))
        if not entries:
            logger.warning("No price history found for %s using Redis key '%s'", currency, redis_key)
            return []
        price_history = []
        for member, score in entries:
            price = parse_history_member_value(member)
            if price > 0:
                price_history.append((int(score), price))
    except REDIS_ERRORS as exc:
        logger.exception("Failed to get %s price history", currency)
        raise RuntimeError(f"Failed to load {currency} price history") from exc
    except (ValueError, TypeError, json.JSONDecodeError):
        logger.exception("Failed to parse %s price history", currency)
        raise
    else:
        return price_history
