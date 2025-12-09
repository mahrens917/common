from __future__ import annotations

"""Probability retrieval helpers."""


from typing import Awaitable, Callable, Dict, List, Optional, Union

from redis.asyncio import Redis

from .probabilityretrieval_helpers.factory import create_probability_retrieval_components
from .probabilityretrieval_helpers.sorting_helpers import (
    ProbabilityByExpiryGrouped,
    ProbabilityByStrikeType,
)


class ProbabilityRetrieval:
    """Read probability payloads from Redis with fail-fast semantics.

    Provides clean API for retrieving probability data in various formats.
    All implementation logic delegated to specialized helper modules.
    """

    def __init__(self, redis_provider: Callable[[], Awaitable[Redis]]) -> None:
        self._components = create_probability_retrieval_components(redis_provider)

    async def get_probabilities(
        self, currency: str
    ) -> Dict[str, Dict[str, Dict[str, Union[str, float]]]]:
        """Get probabilities from hash: probabilities:{CURRENCY}."""
        return await self._components.get_probabilities(currency)

    async def get_probabilities_human_readable(
        self, currency: str
    ) -> Dict[str, Dict[str, ProbabilityByStrikeType]]:
        """Get probabilities grouped by event title."""
        return await self._components.get_probabilities_human_readable(currency)

    async def get_probability_data(
        self,
        currency: str,
        expiry: str,
        strike: str,
        strike_type: str,
        event_title: Optional[str] = None,
    ) -> Dict[str, Union[str, float]]:
        """Get probability data for specific strike."""
        return await self._components.get_probability_data(
            currency, expiry, strike, strike_type, event_title
        )

    async def get_probabilities_grouped_by_event_type(
        self, currency: str
    ) -> Dict[str, ProbabilityByExpiryGrouped]:
        """Get probabilities grouped by all event types."""
        return await self._components.get_probabilities_grouped_by_event_type(currency)

    async def get_all_event_types(self, currency: str) -> List[str]:
        """Get all unique event types for currency."""
        return await self._components.get_all_event_types(currency)

    async def get_probabilities_by_event_type(
        self, currency: str, event_type: str
    ) -> ProbabilityByExpiryGrouped:
        """Get probabilities filtered by event type."""
        return await self._components.get_probabilities_by_event_type(currency, event_type)

    async def get_event_ticker_for_key(self, pattern: str) -> str:
        """Get event ticker from pattern SYMBOL:expiry:strike:strike_type."""
        return await self._components.get_event_ticker_for_key(pattern)


__all__ = ["ProbabilityRetrieval"]
