"""Delegator for probability ingestion operations."""

from typing import Any, Awaitable, Callable, Dict, Optional

from redis.asyncio import Redis

from ..probability_data_config import ProbabilityData
from .factory import IngestionHelpers, create_ingestion_helpers


class ProbabilityIngestionDelegator:
    """Slim coordinator that delegates all operations to specialized helpers."""

    def __init__(self, redis_provider: Callable[[], Awaitable[Redis]]) -> None:
        self._redis_provider = redis_provider
        self._helpers: Optional[IngestionHelpers] = None

    def _get_helpers(self) -> IngestionHelpers:
        """Lazy-load helpers on first use."""
        if self._helpers is None:
            self._helpers = create_ingestion_helpers(self._redis_provider)
        return self._helpers

    async def store_probabilities(
        self, currency: str, probabilities_data: Dict[str, Dict[str, Dict[str, Any]]]
    ) -> bool:
        """
        Store probabilities in compact format.

        Args:
            currency: Currency code (e.g., "BTC")
            probabilities_data: Nested dict of expiry -> strike -> data

        Returns:
            True if storage successful

        Raises:
            ProbabilityStoreError: If storage fails
        """
        helpers = self._get_helpers()
        return await helpers.compact_store.store_probabilities(currency, probabilities_data)

    async def store_probabilities_human_readable(
        self, currency: str, probabilities_data: Dict[str, Dict[str, Dict[str, float]]]
    ) -> bool:
        """
        Store probabilities in human-readable format.

        Args:
            currency: Currency code (e.g., "BTC")
            probabilities_data: Nested dict of expiry -> strike -> data

        Returns:
            True if storage successful

        Raises:
            ProbabilityStoreError: If storage fails
        """
        helpers = self._get_helpers()
        return await helpers.human_readable_store.store_probabilities_human_readable(
            currency, probabilities_data
        )

    async def store_probability(self, data: ProbabilityData) -> None:
        """
        Store a single probability entry.

        Args:
            data: ProbabilityData configuration object

        Raises:
            ProbabilityStoreError: If storage fails
        """
        helpers = self._get_helpers()
        await helpers.single_store.store_probability(data)
