"""Probability calculation logic for strike ranges."""

import logging
from typing import Optional

from redis.asyncio import Redis

from common.strike_helpers import (
    check_strike_in_range,
    decode_redis_key,
    extract_strike_from_key,
)

from .redis_operations import (
    extract_probability_from_key,
    fetch_probability_keys,
)

logger = logging.getLogger(__name__)


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

    total_probability = 0.0
    matching_strikes = 0

    for key in keys:
        key_str = decode_redis_key(key)
        if not key_str:
            continue

        strike_str = extract_strike_from_key(key_str)
        if not strike_str:
            continue

        if not check_strike_in_range(strike_str, strike_low, strike_high):
            continue

        prob_value = await extract_probability_from_key(redis_client, key_str)
        if prob_value is None:
            continue

        total_probability += prob_value
        matching_strikes += 1

    if matching_strikes == 0:
        logger.warning("No matching strikes found for range [%s, %s]", strike_low, strike_high)
        return None

    logger.debug(
        "Calculated probability %s from %s strikes for range [%s, %s]",
        total_probability,
        matching_strikes,
        strike_low,
        strike_high,
    )
    return total_probability
