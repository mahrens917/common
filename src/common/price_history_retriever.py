"""
Price history retrieval for history tracking

Handles fetching and parsing of price history from Redis hash structure with
time-range filtering and chronological sorting.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Tuple

from src.common.price_history_utils import generate_redis_key, validate_currency
from src.common.redis_protocol.typing import RedisClient, ensure_awaitable
from src.common.time_utils import get_current_utc

from .price_history_connection_manager import REDIS_ERRORS
from .price_history_parser import PriceHistoryParser

logger = logging.getLogger(__name__)


class PriceHistoryRetriever:
    """Retrieves price history from Redis hash structure."""

    def __init__(self):
        self._parser = PriceHistoryParser()

    async def get_history(
        self, client: RedisClient, currency: str, hours: int = 24
    ) -> List[Tuple[int, float]]:
        """Retrieve history via the helper implementation."""
        return await _get_history(self, client, currency, hours)


def _validate_currency(currency: str) -> None:
    validate_currency(currency)


def _generate_redis_key(currency: str) -> str:
    return generate_redis_key(currency)


def _calculate_time_range(hours: int) -> tuple[datetime, datetime]:
    current_time = get_current_utc()
    start_time = current_time - timedelta(hours=hours)
    return start_time, current_time


async def _get_history(
    self, client: RedisClient, currency: str, hours: int = 24
) -> List[Tuple[int, float]]:
    _validate_currency(currency)
    try:
        redis_key = _generate_redis_key(currency)
        hash_data = await ensure_awaitable(client.hgetall(redis_key))
        if not hash_data:
            logger.warning(
                "No price history found for %s using Redis key '%s'", currency, redis_key
            )
            return []
        start_time, _ = _calculate_time_range(hours)
        price_history = []
        for datetime_str, price_str in hash_data.items():
            entry = self._parser.parse_hash_entry(datetime_str, price_str, start_time)
            if entry is not None:
                price_history.append(entry)
        price_history.sort(key=lambda x: x[0])
    except REDIS_ERRORS as exc:
        logger.exception("Failed to get %s price history", currency)
        raise RuntimeError(f"Failed to load {currency} price history") from exc
    except (ValueError, TypeError, json.JSONDecodeError):
        logger.exception("Failed to parse %s price history", currency)
        raise
    else:
        return price_history
