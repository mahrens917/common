from __future__ import annotations

"""Event type filtering operations."""

import logging
from typing import Any, Iterable, List

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from ..codec import decode_probability_hash, decode_redis_key
from ..diagnostics import log_event_type_summary
from ..exceptions import ProbabilityStoreError
from ..keys import parse_probability_key
from .sorting_helpers import (
    ProbabilityByExpiryGrouped,
    ProbabilityByStrike,
    ProbabilityByStrikeType,
    sort_probabilities_by_expiry_and_strike_grouped,
)

logger = logging.getLogger(__name__)


async def get_probabilities_by_event_type(
    redis: Redis, currency: str, event_type: str
) -> ProbabilityByExpiryGrouped:
    """Get probabilities filtered by event type.

    Args:
        redis: Redis client
        currency: Currency code (e.g., "BTC", "ETH")
        event_type: Event type to filter by

    Returns:
        Nested dict: {expiry: {strike_type: {strike: {field: value}}}}
        Sorted by expiry, strike_type, then strike

    Raises:
        ProbabilityStoreError: Redis error or no data found for event type
    """
    currency_upper = currency.upper()
    prefix = f"probabilities:{currency_upper}:"

    try:
        raw_keys = await ensure_awaitable(redis.keys(f"{prefix}*"))
    except REDIS_ERRORS as exc:
        raise ProbabilityStoreError(
            f"Failed to fetch event type {event_type} for {currency_upper}: Redis error {exc}"
        ) from exc

    keys = await filter_keys_by_event_type(redis, raw_keys, event_type)
    if not keys:
        raise ProbabilityStoreError(
            f"No data found for event type '{event_type}' for {currency_upper}"
        )

    result: ProbabilityByExpiryGrouped = {}
    for key in keys:
        expiry, strike_type, strike = parse_probability_key(key)
        data = await ensure_awaitable(redis.hgetall(key))
        if not data:
            raise ProbabilityStoreError(f"Probability payload missing for key {key}")
        processed_data = decode_probability_hash(
            data,
            key_str=key,
            log_nan=False,
            logger_fn=logger.debug,
        )
        expiry_bucket: ProbabilityByStrikeType = result.setdefault(expiry, {})
        strike_type_bucket: ProbabilityByStrike = expiry_bucket.setdefault(strike_type, {})
        strike_type_bucket[strike] = processed_data

    sorted_result = sort_probabilities_by_expiry_and_strike_grouped(result)
    log_event_type_summary(currency_upper, event_type, len(keys), sorted_result)
    return sorted_result


async def filter_keys_by_event_type(
    redis: Redis, raw_keys: Iterable[Any], event_type: str
) -> List[str]:
    """Filter Redis keys by event_type field.

    Args:
        redis: Redis client
        raw_keys: Iterable of raw key bytes/strings
        event_type: Event type to match

    Returns:
        List of decoded key strings matching the event type
    """
    matched: List[str] = []
    for raw_key in raw_keys:
        key_str = decode_redis_key(raw_key)
        stored_event_type = await ensure_awaitable(redis.hget(key_str, "event_type"))
        if not stored_event_type:
            continue

        event_type_value = decode_redis_key(stored_event_type)
        if event_type_value == event_type:
            matched.append(key_str)

    return matched


__all__ = ["get_probabilities_by_event_type", "filter_keys_by_event_type"]
