"""
Model State - Centralized interface for probability model operations.

This module provides a centralized interface for loading probability models from Redis
and calculating probabilities for strike ranges using existing probability store infrastructure.
"""

import logging
from typing import Optional, cast

from redis.asyncio import Redis

from ..redis_protocol.probability_store import ProbabilityStore
from ..redis_protocol.typing import ensure_awaitable
from .modelstate_helpers import (
    ModelProbabilityCalculationError,
    calculate_range_probability,
    create_model_state_from_redis,
)
from .modelstate_helpers import initialization as _modelstate_init_module
from .modelstate_helpers.redis_operations import REDIS_ERRORS

# Error messages
ERR_AVERAGE_PRICE_OUT_OF_RANGE = "Average price must be between 1-100 cents: {value}"

logger = logging.getLogger(__name__)
_modelstate_init_module.ProbabilityStore = ProbabilityStore


class ModelState:
    """
    Centralized ModelState for probability calculations using existing probability store infrastructure.

    Provides probability calculations for strike ranges using the ProbabilityStore
    and probability distribution data stored in Redis.
    """

    def __init__(self, probability_store: ProbabilityStore, currency: str):
        """
        Initialize ModelState with probability store.

        Args:
            probability_store: ProbabilityStore instance
            currency: Currency for probability calculations (e.g., 'BTC', 'ETH')
        """
        self.probability_store = probability_store
        self.currency = currency

    @classmethod
    async def load_redis(cls, redis: Redis, currency: str = "BTC") -> "ModelState":
        """
        Load ModelState from Redis using existing probability store infrastructure.

        Args:
            redis: Redis connection
            currency: Currency for probability calculations

        Returns:
            ModelState instance.

        Raises:
            ModelStateInitializationError: If Redis interaction fails.
            ModelStateUnavailableError: If no probability data exists for the currency.
        """
        probability_store, currency_upper = await create_model_state_from_redis(redis, currency, probability_store_cls=ProbabilityStore)
        return cls(probability_store, currency_upper)

    async def calculate_probability(self, strike_low: float, strike_high: float) -> Optional[float]:
        """
        Calculate probability for a strike range using probability store data.

        Args:
            strike_low: Lower strike bound
            strike_high: Upper strike bound

        Returns:
            Probability as float between 0 and 1, or None if no strikes match the range.

        Raises:
            ModelProbabilityCalculationError: If Redis interaction fails.
            ModelProbabilityDataUnavailable: If no probability data exists for the currency.
        """
        get_client = getattr(self.probability_store, "get_redis_client", None)
        has_get_client_method = hasattr(type(self.probability_store), "get_redis_client")
        try:
            if callable(get_client) and has_get_client_method:
                candidate = get_client()
            else:
                candidate = getattr(self.probability_store, "_get_redis")()
            try:
                redis_client = await ensure_awaitable(candidate)
            except TypeError:  # policy_guard: allow-silent-handler
                redis_client = candidate
        except (*REDIS_ERRORS, RuntimeError) as redis_error:  # policy_guard: allow-silent-handler
            raise ModelProbabilityCalculationError(
                f"Failed to acquire Redis client for probability calculation ({self.currency})"
            ) from redis_error

        return await calculate_range_probability(cast(Redis, redis_client), self.currency, strike_low, strike_high)


__all__ = [
    "ModelState",
]
