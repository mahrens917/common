from __future__ import annotations

"""Single probability data retrieval operations."""


import logging
from typing import Dict, Optional, Union

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS
from ...probability_payloads import normalise_strike_value
from ...typing import ensure_awaitable
from ..codec import decode_redis_key
from ..exceptions import ProbabilityDataNotFoundError, ProbabilityStoreError

logger = logging.getLogger(__name__)


async def get_probability_data(
    redis: Redis,
    currency: str,
    expiry: str,
    strike: str,
    strike_type: str,
    event_title: Optional[str] = None,
) -> Dict[str, Union[str, float]]:
    """Get probability data for a specific strike.

    Args:
        redis: Redis client
        currency: Currency code (e.g., "BTC", "ETH")
        expiry: ISO8601 expiry timestamp
        strike: Strike price (will be normalized)
        strike_type: "bid" or "ask"
        event_title: Optional event title to validate against

    Returns:
        Dict of field names to values (numeric fields as float, others as str)

    Raises:
        ProbabilityDataNotFoundError: No data found for key
        ProbabilityStoreError: Redis error or event title mismatch
    """
    currency_upper = currency.upper()
    try:
        rounded_strike = normalise_strike_value(strike)
    except ValueError:
        rounded_strike = strike

    key = f"probabilities:{currency_upper}:{expiry}:{strike_type}:{rounded_strike}"

    try:
        data = await ensure_awaitable(redis.hgetall(key))
    except REDIS_ERRORS as exc:
        raise ProbabilityStoreError(
            f"Failed to get probability data for {key}: Redis error {exc}"
        ) from exc

    if not data:
        raise ProbabilityDataNotFoundError(currency_upper, context=key)

    result: Dict[str, Union[str, float]] = {}
    for field, value in data.items():
        field_name = decode_redis_key(field)
        value_text = decode_redis_key(value)

        if value_text == "NaN":
            result[field_name] = "NaN"
            logger.debug("Retrieved NaN value for field %s in key %s", field_name, key)
            continue

        try:
            result[field_name] = float(value_text)
        except ValueError:
            result[field_name] = value_text

    if event_title is not None and result.get("event_title") != event_title:
        raise ProbabilityStoreError(
            "Probability payload for {key} does not match requested event title {title}".format(
                key=key,
                title=event_title,
            )
        )

    return result


__all__ = ["get_probability_data"]
