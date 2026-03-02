"""Probability calculation logic for strike ranges."""

import logging
from typing import List, Optional

from redis.asyncio import Redis

from common.strike_helpers import (
    check_strike_in_range,
    decode_redis_key,
    extract_strike_from_key,
)

from ...redis_protocol.typing import ensure_awaitable
from .redis_operations import (
    REDIS_ERRORS,
    ModelProbabilityCalculationError,
    fetch_probability_keys,
)

logger = logging.getLogger(__name__)


def _parse_probability(raw_value: object) -> Optional[float]:
    """Parse a raw probability value from Redis into a float."""
    if raw_value is None:
        return None
    prob_str = raw_value.decode("utf-8") if isinstance(raw_value, bytes) else str(raw_value)
    return float(prob_str)


async def _fetch_probabilities_pipeline(redis_client: Redis, keys: List[str]) -> List[Optional[float]]:
    """Fetch probability values for all keys in a single Redis pipeline round-trip."""
    try:
        async with redis_client.pipeline() as pipe:
            for key in keys:
                pipe.hgetall(key)
            results = await ensure_awaitable(pipe.execute())
    except (*REDIS_ERRORS,) as error:
        raise ModelProbabilityCalculationError(f"Pipeline fetch failed for {len(keys)} keys") from error

    probabilities: List[Optional[float]] = []
    for key, data in zip(keys, results):
        if not data:
            probabilities.append(None)
            continue
        probability_raw = data.get(b"probability")
        if probability_raw is None:
            probability_raw = data.get("probability")
        try:
            probabilities.append(_parse_probability(probability_raw))
        except (TypeError, ValueError) as conversion_error:
            raise ModelProbabilityCalculationError(f"Invalid probability value for key {key}: {probability_raw!r}") from conversion_error
    return probabilities


async def calculate_range_probability(redis_client: Redis, currency: str, strike_low: float, strike_high: float) -> Optional[float]:
    """
    Calculate probability for a strike range.

    Args:
        redis_client: Redis connection
        currency: Currency code
        strike_low: Lower strike bound
        strike_high: Upper strike bound

    Returns:
        Total probability or None if no matching strikes

    Raises:
        ModelProbabilityCalculationError: If Redis interaction fails
        ModelProbabilityDataUnavailable: If no probability data exists
    """
    keys = await fetch_probability_keys(redis_client, currency)

    matching_keys: List[str] = []
    for key in keys:
        key_str = decode_redis_key(key)
        if not key_str:
            continue

        strike_str = extract_strike_from_key(key_str)
        if not strike_str:
            continue

        if not check_strike_in_range(strike_str, strike_low, strike_high):
            continue

        matching_keys.append(key_str)

    if not matching_keys:
        logger.warning("No matching strikes found for range [%s, %s]", strike_low, strike_high)
        return None

    prob_values = await _fetch_probabilities_pipeline(redis_client, matching_keys)

    valid_probs = [p for p in prob_values if p is not None]
    if not valid_probs:
        logger.warning("No matching strikes found for range [%s, %s]", strike_low, strike_high)
        return None

    total_probability = sum(valid_probs)
    matching_strikes = len(valid_probs)

    logger.debug(
        "Calculated probability %s from %s strikes for range [%s, %s]",
        total_probability,
        matching_strikes,
        strike_low,
        strike_high,
    )
    return total_probability
