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
    ProbabilityByStrikeType,
)

ProbabilityByEventTitle = Dict[str, ProbabilityByStrikeType]
HumanReadableProbabilityResult = Mapping[
    str,
    Mapping[str, Mapping[str, Mapping[str, Union[str, float]]]],
]

logger = logging.getLogger(__name__)


async def _scan_probability_keys(redis: Redis, prefix: str) -> list:
    """Scan Redis for all probability keys matching the given prefix."""
    raw_keys: list = []
    scan_cursor = 0
    while True:
        scan_cursor, batch = await redis.scan(scan_cursor, match=f"{prefix}*", count=500)
        raw_keys.extend(batch)
        if scan_cursor == 0:
            break
    return raw_keys


def _decode_key_entry(key_str: str, data: dict) -> tuple:
    """Decode and validate a single probability key entry."""
    expiry, strike_type, strike = parse_probability_key(key_str)
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
    return expiry, str(event_title), strike_type, strike, processed_data


def _insert_probability_entry(
    result: Dict[str, ProbabilityByEventTitle],
    expiry: str,
    event_title: str,
    strike_type: str,
    strike: str,
    processed_data: dict,
) -> None:
    """Insert a decoded probability entry into the nested result dict."""
    event_title_bucket = result.get(expiry)
    if event_title_bucket is None:
        event_title_bucket = {}
        result[expiry] = event_title_bucket

    strike_type_bucket = event_title_bucket.get(event_title)
    if strike_type_bucket is None:
        strike_type_bucket = {}
        event_title_bucket[event_title] = strike_type_bucket

    strike_bucket = strike_type_bucket.get(strike_type)
    if strike_bucket is None:
        strike_bucket = {}
        strike_type_bucket[strike_type] = strike_bucket
    strike_bucket[strike] = processed_data


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
        raw_keys = await _scan_probability_keys(redis, prefix)
    except REDIS_ERRORS as exc:
        raise ProbabilityStoreError(f"Failed to get human-readable probabilities for {currency_upper}: Redis error {exc}") from exc

    if not raw_keys:
        raise ProbabilityDataNotFoundError(currency_upper, "human-readable probabilities")

    decoded_keys = [decode_redis_key(rk) for rk in raw_keys]
    pipe = redis.pipeline()
    for key_str in decoded_keys:
        pipe.hgetall(key_str)
    all_data = await ensure_awaitable(pipe.execute())

    result: Dict[str, ProbabilityByEventTitle] = {}
    for key_str, data in zip(decoded_keys, all_data):
        expiry, event_title, strike_type, strike, processed_data = _decode_key_entry(key_str, data)
        _insert_probability_entry(result, expiry, event_title, strike_type, strike, processed_data)

    log_human_readable_summary(
        currency_upper,
        len(raw_keys),
        cast(HumanReadableProbabilityResult, result),
    )
    return result


__all__ = ["get_probabilities_human_readable"]
