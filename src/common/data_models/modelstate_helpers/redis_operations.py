"""Redis operations for probability data retrieval."""

import asyncio
import logging
from typing import Any, List, Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ...redis_protocol.typing import ensure_awaitable
from ...redis_utils import RedisOperationError

# Error messages
ERR_TIMESTAMP_NOT_DATETIME = "Timestamp must be a datetime object"

logger = logging.getLogger(__name__)

REDIS_ERRORS = (
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


class ModelProbabilityCalculationError(RuntimeError):
    """Raised when a probability calculation fails due to Redis or data errors."""


class ModelProbabilityDataUnavailable(ModelProbabilityCalculationError):
    """Raised when no strike data is available for the requested probability query."""


async def fetch_probability_keys(redis_client: Redis, currency: str) -> List[Any]:
    """
    Fetch all probability keys for the given currency.

    Args:
        redis_client: Redis connection
        currency: Currency code (e.g., 'BTC')

    Returns:
        List of Redis keys

    Raises:
        ModelProbabilityCalculationError: If Redis interaction fails
        ModelProbabilityDataUnavailable: If no keys found
    """
    key_pattern = f"probabilities:{currency}:*"

    try:
        keys = await ensure_awaitable(redis_client.keys(key_pattern))
    except (*REDIS_ERRORS, ValueError, TypeError, UnicodeDecodeError) as error:  # policy_guard: allow-silent-handler
        raise ModelProbabilityCalculationError(f"Failed to retrieve probability keys for {currency}") from error

    if not keys:
        raise ModelProbabilityDataUnavailable(f"No probability data available for {currency}")

    return keys


async def extract_probability_from_key(redis_client: Redis, key_str: str) -> Optional[float]:
    """
    Extract probability value from Redis hash.

    Args:
        redis_client: Redis connection
        key_str: Redis key string

    Returns:
        Probability value or None if key has no probability field

    Raises:
        ModelProbabilityCalculationError: If Redis operation fails or probability value is invalid
    """
    try:
        data = await ensure_awaitable(redis_client.hgetall(key_str))
    except REDIS_ERRORS as error:  # policy_guard: allow-silent-handler
        raise ModelProbabilityCalculationError(f"Failed to fetch data for key {key_str}") from error

    probability_raw = None
    if data:
        probability_raw = data.get(b"probability")
        if probability_raw is None:
            probability_raw = data.get("probability")
    if probability_raw is None:
        return None

    try:
        prob_str = probability_raw.decode("utf-8") if isinstance(probability_raw, bytes) else str(probability_raw)
        return float(prob_str)
    except (TypeError, ValueError) as conversion_error:  # policy_guard: allow-silent-handler
        raise ModelProbabilityCalculationError(f"Invalid probability value for key {key_str}: {probability_raw!r}") from conversion_error
