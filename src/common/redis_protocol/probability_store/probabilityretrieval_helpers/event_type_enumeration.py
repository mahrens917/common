from __future__ import annotations

"""Event type enumeration operations."""


import logging
from typing import List

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from ..codec import decode_redis_key
from ..exceptions import ProbabilityDataNotFoundError, ProbabilityStoreError

logger = logging.getLogger(__name__)


async def get_all_event_types(redis: Redis, currency: str) -> List[str]:
    """Get all unique event types for a currency.

    Args:
        redis: Redis client
        currency: Currency code (e.g., "BTC", "ETH")

    Returns:
        Sorted list of event type strings

    Raises:
        ProbabilityDataNotFoundError: No keys found for currency
        ProbabilityStoreError: Redis error or no event types found
    """
    currency_upper = currency.upper()
    prefix = f"probabilities:{currency_upper}:"

    try:
        raw_keys = await redis.keys(f"{prefix}*")
    except REDIS_ERRORS as exc:
        raise ProbabilityStoreError(
            f"Failed to enumerate event types for {currency_upper}: Redis error {exc}"
        ) from exc

    if not raw_keys:
        raise ProbabilityDataNotFoundError(currency_upper, "event types")

    event_types = set()
    for raw_key in raw_keys:
        key = decode_redis_key(raw_key)
        value = await ensure_awaitable(redis.hget(key, "event_type"))
        if not value:
            continue
        decoded = decode_redis_key(value)
        if decoded == "null":
            continue
        event_types.add(decoded)

    if not event_types:
        raise ProbabilityStoreError(f"No event types found for {currency_upper}")

    return sorted(event_types)


__all__ = ["get_all_event_types"]
