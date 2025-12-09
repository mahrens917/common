from __future__ import annotations

"""Probability ingestion helpers."""

import logging
from typing import Any, Awaitable, Callable, Dict

from redis.asyncio import Redis

from .diagnostics import log_failure_context
from .exceptions import ProbabilityStoreError
from .probability_data_config import ProbabilityData
from .probabilityingestion_helpers import (
    HumanReadableIngestionStats,
    ProbabilityIngestionDelegator,
)
from .verification import run_direct_connectivity_test

logger = logging.getLogger(__name__)


class ProbabilityIngestion:
    """Handle persistence of probability payloads."""

    def __init__(self, redis_provider: Callable[[], Awaitable[Redis]]) -> None:
        self._delegator = ProbabilityIngestionDelegator(redis_provider)
        self._redis_provider = redis_provider

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
        return await self._delegator.store_probabilities(currency, probabilities_data)

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
        return await self._delegator.store_probabilities_human_readable(
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
        await self._delegator.store_probability(data)


async def handle_ingestion_failure(
    redis: Redis,
    currency: str,
    probabilities_data: Dict[str, Dict[str, Dict[str, float]]],
    exc: Exception,
) -> None:
    """
    Handle ingestion failure by logging context and testing connectivity.

    Args:
        redis: Redis client
        currency: Currency code
        probabilities_data: The data that failed to ingest
        exc: The exception that occurred

    Raises:
        ProbabilityStoreError: Always raises with context
    """
    log_failure_context(probabilities_data)
    await run_direct_connectivity_test(redis, currency)
    raise ProbabilityStoreError(
        f"Failed to store human-readable probabilities for {currency}"
    ) from exc


__all__ = ["ProbabilityIngestion", "HumanReadableIngestionStats", "handle_ingestion_failure"]
