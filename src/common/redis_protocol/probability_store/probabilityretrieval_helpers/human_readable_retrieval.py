from __future__ import annotations

"""Human-readable probability retrieval operations."""


import logging
from typing import Dict, Mapping, Union, cast

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from ..codec import decode_probability_hash, decode_redis_key
from ..diagnostics import log_human_readable_summary
from ..exceptions import ProbabilityDataNotFoundError, ProbabilityStoreError
from ..keys import parse_probability_key
from .sorting_helpers import (
    ProbabilityByStrike,
    ProbabilityByStrikeType,
)

ProbabilityByEventTitle = Dict[str, ProbabilityByStrikeType]
HumanReadableProbabilityResult = Mapping[
    str,
    Mapping[str, Mapping[str, Mapping[str, Union[str, float]]]],
]

logger = logging.getLogger(__name__)


async def get_probabilities_human_readable(redis: Redis, currency: str) -> Dict[str, ProbabilityByEventTitle]:
    """Get probabilities in human-readable format grouped by event title.

    Retrieves from `probabilities:{CURRENCY}:{expiry}:{strike_type}:{strike}` keys.

    Args:
        redis: Redis client
        currency: Currency code (e.g., "BTC", "ETH")

    Returns:
        Nested dict: {expiry: {event_title: {strike_type: {strike: {field: value}}}}}

    Raises:
        ProbabilityDataNotFoundError: No keys found for currency
        ProbabilityStoreError: Redis error or missing required fields
    """
    currency_upper = currency.upper()
    logger.debug("Getting human-readable probabilities for %s", currency_upper)

    prefix = f"probabilities:{currency_upper}:"

    try:
        raw_keys = await redis.keys(f"{prefix}*")
    except REDIS_ERRORS as exc:
        raise ProbabilityStoreError(f"Failed to get human-readable probabilities for {currency_upper}: Redis error {exc}") from exc

    if not raw_keys:
        raise ProbabilityDataNotFoundError(currency_upper, "human-readable probabilities")

    result: Dict[str, ProbabilityByEventTitle] = {}

    for raw_key in raw_keys:
        key_str = decode_redis_key(raw_key)
        expiry, strike_type, strike = parse_probability_key(key_str)

        data = await ensure_awaitable(redis.hgetall(key_str))
        if not data:
            raise ProbabilityStoreError(f"Probability payload missing for key {key_str} while building human-readable view")

        processed_data = decode_probability_hash(
            data,
            key_str=key_str,
            log_nan=True,
            logger_fn=logger.debug,
        )
        event_title = processed_data.get("event_title")
        if event_title is None:
            raise ProbabilityStoreError(f"Missing event_title for key {key_str}")

        event_title_bucket: ProbabilityByEventTitle = result.setdefault(expiry, {})
        strike_type_bucket: ProbabilityByStrikeType = event_title_bucket.setdefault(str(event_title), {})
        strike_bucket: ProbabilityByStrike = strike_type_bucket.setdefault(strike_type, {})
        strike_bucket[strike] = processed_data

    log_human_readable_summary(
        currency_upper,
        len(raw_keys),
        cast(HumanReadableProbabilityResult, result),
    )
    return result


__all__ = ["get_probabilities_human_readable"]
