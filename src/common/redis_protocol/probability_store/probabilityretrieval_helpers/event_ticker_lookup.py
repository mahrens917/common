from __future__ import annotations

"""Event ticker lookup operations."""


import logging

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from ..codec import decode_redis_key
from ..exceptions import ProbabilityDataNotFoundError, ProbabilityStoreError

logger = logging.getLogger(__name__)


async def get_event_ticker_for_key(redis: Redis, pattern: str) -> str:
    """Get event ticker from a probability key pattern.

    Args:
        redis: Redis client
        pattern: Pattern in format "SYMBOL:expiry:strike:strike_type"

    Returns:
        Event ticker string

    Raises:
        ProbabilityStoreError: Invalid pattern or Redis error
        ProbabilityDataNotFoundError: Key not found or no event_ticker field
    """
    parts = pattern.split(":")
    if len(parts) < _CONST_4:
        raise ProbabilityStoreError(f"Invalid pattern for event type lookup: {pattern}")

    symbol, expiry, strike, strike_type = parts[0], parts[1], parts[2], parts[3]
    redis_key = f"probabilities:{symbol}:{expiry}:{strike_type}:{strike}"

    try:
        key_data = await ensure_awaitable(redis.hgetall(redis_key))
    except REDIS_ERRORS as exc:
        raise ProbabilityStoreError(f"Failed to get event ticker for key {pattern}: Redis error {exc}") from exc

    if not key_data:
        raise ProbabilityDataNotFoundError(symbol, context=redis_key)

    for field, value in key_data.items():
        field_str = decode_redis_key(field)
        value_str = decode_redis_key(value)
        if field_str == "event_ticker" and value_str:
            return value_str

    raise ProbabilityStoreError(f"No event_ticker found for key {redis_key}")


# Constants
_CONST_4 = 4

__all__ = ["get_event_ticker_for_key"]
