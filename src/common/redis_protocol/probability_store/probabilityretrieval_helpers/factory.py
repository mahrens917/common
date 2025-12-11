from __future__ import annotations

"""Factory for creating probability retrieval components."""

from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from redis.asyncio import Redis

from ..redis_provider_mixin import RedisProviderMixin
from . import (
    basic_retrieval,
    event_ticker_lookup,
    event_type_enumeration,
    event_type_filtering,
    grouped_retrieval,
    human_readable_retrieval,
    single_probability_retrieval,
)


class ProbabilityRetrievalComponents(RedisProviderMixin):
    """Container for probability retrieval helper functions.

    All methods are bound to a Redis provider for consistent connection handling.
    """

    async def get_probabilities(self, currency: str):
        """Delegate to basic_retrieval.get_probabilities."""
        redis = await self._get_redis()
        return await basic_retrieval.get_probabilities(redis, currency)

    async def get_probabilities_human_readable(self, currency: str):
        """Delegate to human_readable_retrieval.get_probabilities_human_readable."""
        redis = await self._get_redis()
        return await human_readable_retrieval.get_probabilities_human_readable(redis, currency)

    async def get_probability_data(self, currency: str, expiry: str, strike: str, strike_type: str, event_title=None):
        """Delegate to single_probability_retrieval.get_probability_data."""
        redis = await self._get_redis()
        return await single_probability_retrieval.get_probability_data(redis, currency, expiry, strike, strike_type, event_title)

    async def get_probabilities_grouped_by_event_type(self, currency: str):
        """Delegate to grouped_retrieval.get_probabilities_grouped_by_event_type."""
        redis = await self._get_redis()
        return await grouped_retrieval.get_probabilities_grouped_by_event_type(redis, currency)

    async def get_all_event_types(self, currency: str):
        """Delegate to event_type_enumeration.get_all_event_types."""
        redis = await self._get_redis()
        return await event_type_enumeration.get_all_event_types(redis, currency)

    async def get_probabilities_by_event_type(self, currency: str, event_type: str):
        """Delegate to event_type_filtering.get_probabilities_by_event_type."""
        redis = await self._get_redis()
        return await event_type_filtering.get_probabilities_by_event_type(redis, currency, event_type)

    async def get_event_ticker_for_key(self, pattern: str):
        """Delegate to event_ticker_lookup.get_event_ticker_for_key."""
        redis = await self._get_redis()
        return await event_ticker_lookup.get_event_ticker_for_key(redis, pattern)


def create_probability_retrieval_components(
    redis_provider: Callable[[], Awaitable[Redis]],
) -> ProbabilityRetrievalComponents:
    """Create probability retrieval components with dependency injection.

    Args:
        redis_provider: Async callable that returns Redis client

    Returns:
        Configured ProbabilityRetrievalComponents instance
    """
    return ProbabilityRetrievalComponents(redis_provider)


__all__ = ["ProbabilityRetrievalComponents", "create_probability_retrieval_components"]
