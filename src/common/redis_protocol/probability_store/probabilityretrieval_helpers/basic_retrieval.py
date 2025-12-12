from __future__ import annotations

"""Basic probability retrieval operations."""


import logging
from typing import Dict, Union

import orjson
from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from ..codec import decode_redis_key
from ..exceptions import ProbabilityDataNotFoundError, ProbabilityStoreError
from .sorting_helpers import sort_probabilities_by_expiry_and_strike, split_probability_field

logger = logging.getLogger(__name__)


async def get_probabilities(redis: Redis, currency: str) -> Dict[str, Dict[str, Dict[str, Union[str, float]]]]:
    """Get all probabilities for a currency from the hash format.

    Retrieves from `probabilities:{CURRENCY}` hash where fields are "expiry:strike"
    and values are JSON payloads.

    Args:
        redis: Redis client
        currency: Currency code (e.g., "BTC", "ETH")

    Returns:
        Nested dict: {expiry: {strike: {field: value}}}
        Sorted by expiry (chronological) then strike (numeric)

    Raises:
        ProbabilityDataNotFoundError: No data found for currency
        ProbabilityStoreError: Redis error or JSON decode error
    """
    currency_upper = currency.upper()
    key = f"probabilities:{currency_upper}"
    logger.info("Getting probabilities for %s with key: %s", currency_upper, key)

    try:
        all_data = await ensure_awaitable(redis.hgetall(key))
    except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
        raise ProbabilityStoreError(f"Failed to get probabilities for {currency_upper}: Redis error {exc}") from exc

    if not all_data:
        raise ProbabilityDataNotFoundError(currency_upper)

    result: Dict[str, Dict[str, Dict[str, Union[str, float]]]] = {}
    for raw_field, raw_value in all_data.items():
        field = decode_redis_key(raw_field)
        value_text = decode_redis_key(raw_value)
        expiry, strike = split_probability_field(field)

        try:
            payload = orjson.loads(value_text)
        except orjson.JSONDecodeError as exc:  # policy_guard: allow-silent-handler
            raise ProbabilityStoreError(f"Error parsing probability payload for field {field}: {value_text}") from exc

        expiry_bucket = result.setdefault(expiry, {})
        strike_bucket = expiry_bucket.setdefault(strike, {})
        for key_name, key_value in payload.items():
            strike_bucket[key_name] = key_value

    return sort_probabilities_by_expiry_and_strike(result)


__all__ = ["get_probabilities"]
