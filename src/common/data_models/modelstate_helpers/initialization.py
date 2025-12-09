"""Model state initialization and validation logic."""

import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ...redis_protocol.probability_store import ProbabilityStore
from ...redis_utils import RedisOperationError

# Error messages
ERR_LAST_UPDATED_NOT_DATETIME = "Last updated must be a datetime object"

logger = logging.getLogger(__name__)

REDIS_ERRORS = (
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


class ModelStateError(RuntimeError):
    """Base exception for model state operations."""


class ModelStateInitializationError(ModelStateError):
    """Raised when the model state cannot be initialized from Redis."""


class ModelStateUnavailableError(ModelStateError):
    """Raised when no probability data is available for the requested currency."""


async def initialize_probability_store(currency: str) -> ProbabilityStore:
    """
    Initialize probability store for given currency.

    Args:
        currency: Currency for probability calculations

    Returns:
        ProbabilityStore instance

    Raises:
        ModelStateInitializationError: If Redis interaction fails
    """
    raise NotImplementedError("Probability store initialization requires Redis instance")


async def validate_currency_data(redis: Redis, currency: str) -> int:
    """
    Validate that probability data exists for the currency.

    Args:
        redis: Redis connection
        currency: Currency to validate

    Returns:
        Number of probability keys found

    Raises:
        ModelStateInitializationError: If Redis interaction fails
        ModelStateUnavailableError: If no probability data exists
    """
    currency_upper = currency.upper()
    key_pattern = f"probabilities:{currency_upper}:*"

    try:
        keys = await redis.keys(key_pattern)
    except (*REDIS_ERRORS, RuntimeError) as error:
        raise ModelStateInitializationError(
            f"Failed to list probability keys for {currency}"
        ) from error

    if not keys:
        raise ModelStateUnavailableError(f"No probability data found for {currency}")

    logger.info("Found %d probability keys for %s", len(keys), currency)
    return len(keys)


async def create_model_state_from_redis(
    redis: Redis, currency: str, *, probability_store_cls=ProbabilityStore
) -> tuple[ProbabilityStore, str]:
    """
    Create ModelState components from Redis.

    Args:
        redis: Redis connection
        currency: Currency for probability calculations

    Returns:
        Tuple of (probability_store, currency_upper)

    Raises:
        ModelStateInitializationError: If Redis interaction fails
        ModelStateUnavailableError: If no probability data exists
    """
    try:
        probability_store = probability_store_cls(redis)
    except REDIS_ERRORS as error:
        raise ModelStateInitializationError(
            f"Failed to initialize ProbabilityStore for {currency}"
        ) from error

    currency_upper = currency.upper()
    await validate_currency_data(redis, currency)

    return probability_store, currency_upper
