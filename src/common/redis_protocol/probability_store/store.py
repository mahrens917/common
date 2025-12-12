from __future__ import annotations

"""Orchestrator for probability store operations."""

import logging
from typing import Any, Dict, Optional, Union

from redis.asyncio import Redis

from ..error_types import REDIS_ERRORS
from .exceptions import (
    ProbabilityDataNotFoundError,
    ProbabilityStoreError,
    ProbabilityStoreInitializationError,
)
from .ingestion import ProbabilityIngestion
from .probability_data_config import ProbabilityData
from .probabilityretrieval_helpers.sorting_helpers import (
    ProbabilityByExpiryGrouped,
    ProbabilityByStrikeType,
)
from .retrieval import ProbabilityRetrieval

logger = logging.getLogger(__name__)


class ProbabilityStore:
    """Fail-fast Redis store for probability data."""

    def __init__(self, redis: Optional[Redis] = None) -> None:
        self.redis: Optional[Redis] = redis
        self._initialized = redis is not None
        self._ingestion = ProbabilityIngestion(self._get_redis)
        self._retrieval = ProbabilityRetrieval(self._get_redis)

    def initialize(self, redis: Redis) -> None:
        """Explicitly set the Redis connection."""
        self.redis = redis
        self._initialized = True

    async def _get_redis(self) -> Redis:
        if not self._initialized or self.redis is None:
            raise ProbabilityStoreInitializationError()
        return self.redis

    async def get_redis_client(self) -> Redis:
        """Public accessor for the underlying Redis client."""
        return await self._get_redis()

    async def store_probabilities(self, currency: str, probabilities_data: Dict[str, Any]) -> bool:
        try:
            return await self._ingestion.store_probabilities(currency, probabilities_data)
        except ProbabilityStoreError:  # policy_guard: allow-silent-handler
            raise
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            raise ProbabilityStoreError(f"Failed to store probabilities for {currency.upper()}: Redis error {exc}") from exc

    async def store_probabilities_human_readable(self, currency: str, probabilities_data: Dict[str, Dict[str, Dict[str, float]]]) -> bool:
        return await self._ingestion.store_probabilities_human_readable(currency, probabilities_data)

    async def store_probability(self, data: ProbabilityData) -> None:
        """Store a single probability entry.

        Args:
            data: ProbabilityData object containing all required fields
        """
        await self._ingestion.store_probability(data)

    async def get_probabilities(self, currency: str) -> Dict[str, Dict[str, Dict[str, Union[str, float]]]]:
        return await self._retrieval.get_probabilities(currency)

    async def get_probabilities_human_readable(self, currency: str) -> Dict[str, Dict[str, ProbabilityByStrikeType]]:
        return await self._retrieval.get_probabilities_human_readable(currency)

    async def get_probability_data(
        self,
        currency: str,
        expiry: str,
        strike: str,
        strike_type: str,
        event_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._retrieval.get_probability_data(currency, expiry, strike, strike_type, event_title)

    async def get_probabilities_grouped_by_event_type(self, currency: str) -> Dict[str, ProbabilityByExpiryGrouped]:
        return await self._retrieval.get_probabilities_grouped_by_event_type(currency)

    async def get_all_event_types(self, currency: str) -> list[str]:
        return await self._retrieval.get_all_event_types(currency)

    async def get_probabilities_by_event_type(self, currency: str, event_type: str) -> ProbabilityByExpiryGrouped:
        return await self._retrieval.get_probabilities_by_event_type(currency, event_type)

    async def get_event_ticker_for_key(self, pattern: str) -> str:
        return await self._retrieval.get_event_ticker_for_key(pattern)


__all__ = ["ProbabilityStore", "ProbabilityStoreError", "ProbabilityDataNotFoundError"]
