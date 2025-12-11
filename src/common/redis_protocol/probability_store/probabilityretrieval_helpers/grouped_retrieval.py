from __future__ import annotations

"""Grouped probability retrieval operations."""


from typing import Dict, List

from redis.asyncio import Redis

from .event_type_enumeration import get_all_event_types
from .event_type_filtering import get_probabilities_by_event_type
from .sorting_helpers import ProbabilityByExpiryGrouped


async def get_probabilities_grouped_by_event_type(redis: Redis, currency: str) -> Dict[str, ProbabilityByExpiryGrouped]:
    """Get probabilities grouped by all event types.

    This is a convenience method that calls get_all_event_types and then
    get_probabilities_by_event_type for each type.

    Args:
        redis: Redis client
        currency: Currency code (e.g., "BTC", "ETH")

    Returns:
        Dict mapping event_type to probability data:
        {event_type: {expiry: {strike_type: {strike: {field: value}}}}}

    Raises:
        ProbabilityDataNotFoundError: No event types found
        ProbabilityStoreError: Redis error
    """
    event_types: List[str] = await get_all_event_types(redis, currency)
    result: Dict[str, ProbabilityByExpiryGrouped] = {}

    for event_type in event_types:
        result[event_type] = await get_probabilities_by_event_type(redis, currency, event_type)

    return result


__all__ = ["get_probabilities_grouped_by_event_type"]
