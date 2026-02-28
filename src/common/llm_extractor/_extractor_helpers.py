"""Helper functions for market extraction services."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from ..redis_protocol.typing import ensure_awaitable

if TYPE_CHECKING:
    from .client import AnthropicClient

from ._response_parser import (
    ExtraDataInResponse,
    parse_kalshi_underlying_batch_response,
    parse_kalshi_underlying_response,
    parse_poly_batch_response,
    parse_poly_extraction_response,
)
from .models import MarketExtraction
from .prompts import (
    build_kalshi_underlying_batch_prompt,
    build_kalshi_underlying_batch_user_content,
    build_kalshi_underlying_prompt,
    build_kalshi_underlying_user_content,
    build_poly_batch_user_content,
    build_poly_prompt,
    build_poly_user_content,
)

logger = logging.getLogger(__name__)

_TTL_SECONDS = 604800  # 7 days
_REDIS_PREFIX_KALSHI = "market:extracted:kalshi"
_REDIS_PREFIX_POLY = "market:extracted:poly"
_BATCH_SIZE = 10
_CONCURRENT_REQUESTS = 5

# Minimum underlyings required for dedup
_MIN_UNDERLYINGS_FOR_DEDUP = 2


def get_redis_key(market_id: str, platform: str) -> str:
    """Generate Redis key for extracted fields."""
    if platform == "kalshi":
        return f"{_REDIS_PREFIX_KALSHI}:{market_id}"
    return f"{_REDIS_PREFIX_POLY}:{market_id}"


def get_ttl() -> int:
    """Return TTL in seconds."""
    return _TTL_SECONDS


def get_batch_size() -> int:
    """Return batch size for processing."""
    return _BATCH_SIZE


def get_concurrent_requests() -> int:
    """Return concurrent requests limit."""
    return _CONCURRENT_REQUESTS


def get_min_underlyings_for_dedup() -> int:
    """Return minimum underlyings required for dedup."""
    return _MIN_UNDERLYINGS_FOR_DEDUP


async def extract_kalshi_single(
    client: "AnthropicClient",
    market: dict,
    existing_underlyings: list[str],
) -> str | None:
    """Extract underlying for a single Kalshi market."""
    prompt = build_kalshi_underlying_prompt(existing_underlyings)
    user_content = build_kalshi_underlying_user_content(
        title=market["title"],
        rules_primary=market["rules_primary"],
        category=market["category"],
    )
    response = await client.send_message(prompt, user_content)
    return parse_kalshi_underlying_response(response.text)


async def extract_kalshi_batch_with_retry(
    client: "AnthropicClient",
    batch: list[dict],
    existing_underlyings: list[str],
    redis: Redis,
) -> dict[str, str]:
    """Extract underlyings for a batch with retry for failed items."""
    prompt = build_kalshi_underlying_batch_prompt(existing_underlyings)
    user_content = build_kalshi_underlying_batch_user_content(batch)
    original_ids = [m["id"] for m in batch]

    for attempt in range(2):
        response = await client.send_message(prompt, user_content, json_prefill='{"markets": [')
        try:
            results, failed_ids = parse_kalshi_underlying_batch_response(response.text, original_ids)
            break
        except ExtraDataInResponse as e:
            if attempt == 0:
                logger.debug("Extra data in Kalshi batch response, retrying: %s", e.extra_text[:100])
                continue
            raise

    if failed_ids:
        logger.debug("Retrying %d failed Kalshi extractions", len(failed_ids))
        failed_markets = [m for m in batch if m["id"] in failed_ids]
        for market in failed_markets:
            underlying = await extract_kalshi_single(client, market, existing_underlyings)
            if underlying:
                results[market["id"]] = underlying

    await store_kalshi_cached_batch(results, redis)
    return results


async def load_kalshi_cached(market_id: str, redis: Redis) -> str | None:
    """Load cached underlying from Redis."""
    key = get_redis_key(market_id, "kalshi")
    data = await ensure_awaitable(redis.hgetall(key))
    if data and "underlying" in data:
        return data["underlying"]
    return None


async def store_kalshi_cached_batch(results: dict[str, str], redis: Redis) -> None:
    """Store batch of underlyings in Redis cache."""
    if not results:
        return

    pipe = redis.pipeline()
    for market_id, underlying in results.items():
        key = get_redis_key(market_id, "kalshi")
        pipe.hset(key, mapping={"underlying": underlying})
        pipe.expire(key, get_ttl())

    await pipe.execute()


async def extract_poly_single_with_retry(
    client: "AnthropicClient",
    market: dict,
    valid_categories: set[str],
    valid_underlyings: set[str],
) -> MarketExtraction | None:
    """Extract single Poly market with one retry."""
    prompt = build_poly_prompt(list(valid_categories), list(valid_underlyings))
    user_content = build_poly_user_content(
        title=market["title"],
        description=market["description"],
    )

    response = await client.send_message(prompt, user_content)
    extraction, error = parse_poly_extraction_response(response.text, market["id"], valid_categories, valid_underlyings)
    if extraction:
        return extraction

    logger.debug("First attempt failed for %s: %s, retrying", market["id"], error)

    response = await client.send_message(prompt, user_content)
    extraction, error = parse_poly_extraction_response(response.text, market["id"], valid_categories, valid_underlyings)
    if extraction:
        return extraction

    logger.debug("Retry failed for %s: %s, skipping", market["id"], error)
    return None


async def _retry_failed_poly_extractions(
    client: "AnthropicClient",
    batch: list[dict],
    failed_ids: list[str],
    valid_categories: set[str],
    valid_underlyings: set[str],
) -> tuple[list[MarketExtraction], list[str]]:
    """Retry individual Poly extractions for failed batch items."""
    results: list[MarketExtraction] = []
    no_match_ids: list[str] = []
    logger.debug("Retrying %d failed Poly extractions", len(failed_ids))
    failed_markets = [m for m in batch if m["id"] in failed_ids]
    for market in failed_markets:
        extraction = await extract_poly_single_with_retry(client, market, valid_categories, valid_underlyings)
        if extraction:
            results.append(extraction)
        else:
            no_match_ids.append(market["id"])
    return results, no_match_ids


async def extract_poly_batch_with_retry(
    client: "AnthropicClient",
    batch: list[dict],
    valid_categories: set[str],
    valid_underlyings: set[str],
    redis: Redis,
) -> list[MarketExtraction]:
    """Extract a Poly batch with retry for failed items."""
    prompt = build_poly_prompt(list(valid_categories), list(valid_underlyings))
    user_content = build_poly_batch_user_content(batch)
    original_ids = [m["id"] for m in batch]

    extractions: dict[str, MarketExtraction] = {}
    failed_ids: list[str] = []
    batch_no_match_ids: list[str] = []
    for attempt in range(2):
        response = await client.send_message(prompt, user_content, json_prefill='{"markets": [')
        try:
            extractions, failed_ids, batch_no_match_ids = parse_poly_batch_response(
                response.text, valid_categories, valid_underlyings, original_ids
            )
            break
        except ExtraDataInResponse as e:
            if attempt == 0:
                logger.debug("Extra data in Poly batch response, retrying: %s", e.extra_text[:100])
                continue
            raise

    results = list(extractions.values())

    if failed_ids:
        retried, retry_no_match_ids = await _retry_failed_poly_extractions(
            client,
            batch,
            failed_ids,
            valid_categories,
            valid_underlyings,
        )
        results.extend(retried)
        no_match_ids = batch_no_match_ids + retry_no_match_ids
    else:
        no_match_ids = batch_no_match_ids

    await store_poly_cached_batch(results, redis)

    if no_match_ids:
        await store_poly_no_match_batch(no_match_ids, redis)

    return results


async def load_poly_cached_batch(
    markets: list[dict],
    redis: Redis,
) -> tuple[list[MarketExtraction], list[dict]]:
    """Load cached Poly extractions from Redis."""
    cached: list[MarketExtraction] = []
    uncached: list[dict] = []
    skipped_no_match = 0

    for market in markets:
        market_id = market["id"]
        key = get_redis_key(market_id, "poly")
        data = await ensure_awaitable(redis.hgetall(key))

        if data:
            if data.get("status") == "no_match":
                skipped_no_match += 1
                continue

            if "category" in data and "underlying" in data:
                extraction = MarketExtraction(
                    market_id=market_id,
                    platform="poly",
                    category=data["category"],
                    underlying=data["underlying"],
                    strike_type=data.get("strike_type"),
                    floor_strike=float(data["floor_strike"]) if data.get("floor_strike") else None,
                    cap_strike=float(data["cap_strike"]) if data.get("cap_strike") else None,
                    close_time=data.get("close_time"),
                )
                cached.append(extraction)
                continue

        uncached.append(market)

    if cached or skipped_no_match:
        logger.info(
            "Poly cache: %d matched, %d no-match skipped, %d to extract",
            len(cached),
            skipped_no_match,
            len(uncached),
        )

    return cached, uncached


async def store_poly_cached_batch(extractions: list[MarketExtraction], redis: Redis) -> None:
    """Store Poly extractions in Redis cache."""
    if not extractions:
        return

    pipe = redis.pipeline()
    for extraction in extractions:
        key = get_redis_key(extraction.market_id, "poly")
        field_map: dict[str, str] = {
            "category": extraction.category,
            "underlying": extraction.underlying,
        }
        if extraction.strike_type:
            field_map["strike_type"] = extraction.strike_type
        if extraction.floor_strike is not None:
            field_map["floor_strike"] = str(extraction.floor_strike)
        if extraction.cap_strike is not None:
            field_map["cap_strike"] = str(extraction.cap_strike)
        if extraction.close_time:
            field_map["close_time"] = extraction.close_time

        pipe.hset(key, mapping=field_map)
        pipe.expire(key, get_ttl())

    await pipe.execute()


async def store_poly_no_match_batch(market_ids: list[str], redis: Redis) -> None:
    """Store no-match markers in Redis cache."""
    if not market_ids:
        return

    pipe = redis.pipeline()
    for market_id in market_ids:
        key = get_redis_key(market_id, "poly")
        pipe.hset(key, mapping={"status": "no_match"})
        pipe.expire(key, get_ttl())

    await pipe.execute()
    logger.debug("Cached %d no-match Poly markets", len(market_ids))


__all__ = [
    "get_redis_key",
    "get_ttl",
    "get_batch_size",
    "get_concurrent_requests",
    "get_min_underlyings_for_dedup",
    "extract_kalshi_single",
    "extract_kalshi_batch_with_retry",
    "load_kalshi_cached",
    "store_kalshi_cached_batch",
    "extract_poly_single_with_retry",
    "extract_poly_batch_with_retry",
    "load_poly_cached_batch",
    "store_poly_cached_batch",
    "store_poly_no_match_batch",
]
