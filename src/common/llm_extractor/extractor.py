"""MarketExtractor: batch extraction with Redis caching."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Sequence, cast

from redis.asyncio import Redis

if TYPE_CHECKING:
    from collections.abc import Coroutine

from ._response_parser import parse_batch_response
from .client import AnthropicClient
from .models import MarketExtraction
from .prompts import EXTRACTION_PROMPT, build_user_content

logger = logging.getLogger(__name__)

_BATCH_SIZE = 10
_CONCURRENT_REQUESTS = 5
_TTL_KALSHI_SECONDS = 604800  # 7 days
_TTL_POLY_SECONDS = 604800  # 7 days
_REDIS_PREFIX_KALSHI = "market:extracted:kalshi"
_REDIS_PREFIX_POLY = "market:extracted:poly"


def _get_redis_key(market_id: str, platform: str) -> str:
    """Generate Redis key for extracted fields."""
    if platform == "kalshi":
        return f"{_REDIS_PREFIX_KALSHI}:{market_id}"
    return f"{_REDIS_PREFIX_POLY}:{market_id}"


def _get_ttl(platform: str) -> int:
    """Return TTL in seconds based on platform."""
    if platform == "kalshi":
        return _TTL_KALSHI_SECONDS
    return _TTL_POLY_SECONDS


def _extraction_to_redis_map(extraction: MarketExtraction) -> dict[str, str]:
    """Convert a MarketExtraction to a Redis hash map."""
    field_map: dict[str, str] = {
        "category": extraction.category,
        "underlying": extraction.underlying,
        "subject": extraction.subject,
        "entity": extraction.entity,
        "scope": extraction.scope,
        "platform": extraction.platform,
        "is_conjunction": str(extraction.is_conjunction),
        "is_union": str(extraction.is_union),
    }
    if extraction.floor_strike is not None:
        field_map["floor_strike"] = str(extraction.floor_strike)
    if extraction.cap_strike is not None:
        field_map["cap_strike"] = str(extraction.cap_strike)
    if extraction.parent_entity is not None:
        field_map["parent_entity"] = extraction.parent_entity
    if extraction.parent_scope is not None:
        field_map["parent_scope"] = extraction.parent_scope
    if extraction.conjunction_scopes:
        field_map["conjunction_scopes"] = json.dumps(extraction.conjunction_scopes)
    if extraction.union_scopes:
        field_map["union_scopes"] = json.dumps(extraction.union_scopes)
    return field_map


def _redis_map_to_extraction(market_id: str, platform: str, data: dict[bytes, bytes]) -> MarketExtraction:
    """Convert a Redis hash map back to a MarketExtraction."""
    category = data[b"category"].decode()
    underlying = data[b"underlying"].decode()
    subject = data[b"subject"].decode()
    entity = data[b"entity"].decode()
    scope = data[b"scope"].decode()

    floor_strike = float(data[b"floor_strike"].decode()) if b"floor_strike" in data else None
    cap_strike = float(data[b"cap_strike"].decode()) if b"cap_strike" in data else None
    parent_entity = data[b"parent_entity"].decode() if b"parent_entity" in data else None
    parent_scope = data[b"parent_scope"].decode() if b"parent_scope" in data else None

    is_conjunction = b"is_conjunction" in data and data[b"is_conjunction"].decode() == "True"
    conjunction_scopes: tuple[str, ...] = ()
    if b"conjunction_scopes" in data:
        conjunction_scopes = tuple(json.loads(data[b"conjunction_scopes"].decode()))

    is_union = b"is_union" in data and data[b"is_union"].decode() == "True"
    union_scopes: tuple[str, ...] = ()
    if b"union_scopes" in data:
        union_scopes = tuple(json.loads(data[b"union_scopes"].decode()))

    return MarketExtraction(
        market_id=market_id,
        platform=platform,
        category=category,
        underlying=underlying,
        subject=subject,
        entity=entity,
        scope=scope,
        floor_strike=floor_strike,
        cap_strike=cap_strike,
        parent_entity=parent_entity,
        parent_scope=parent_scope,
        is_conjunction=is_conjunction,
        conjunction_scopes=conjunction_scopes,
        is_union=is_union,
        union_scopes=union_scopes,
    )


async def _store_extractions(extractions: list[MarketExtraction], redis: Redis) -> None:
    """Store extracted fields in Redis with TTL."""
    pipe = redis.pipeline()
    for extraction in extractions:
        redis_key = _get_redis_key(extraction.market_id, extraction.platform)
        field_map = _extraction_to_redis_map(extraction)
        pipe.hset(redis_key, mapping=field_map)
        pipe.expire(redis_key, _get_ttl(extraction.platform))
    await pipe.execute()


async def _load_cached(markets: Sequence[dict], platform: str, redis: Redis) -> tuple[list[MarketExtraction], list[dict]]:
    """Load cached extractions; return (cached_results, uncached_markets)."""
    cached: list[MarketExtraction] = []
    uncached: list[dict] = []

    for market in markets:
        market_id = market["id"]
        redis_key = _get_redis_key(market_id, platform)
        coro = cast("Coroutine[Any, Any, dict[Any, Any]]", redis.hgetall(redis_key))
        existing = await coro
        if existing and b"category" in existing and b"entity" in existing:
            extraction = _redis_map_to_extraction(market_id, platform, existing)
            cached.append(extraction)
        else:
            uncached.append(market)

    if cached:
        logger.info("Cache hits: %d, need to extract: %d", len(cached), len(uncached))
    return cached, uncached


class MarketExtractor:
    """Batch market extraction service using Claude Opus with Redis caching."""

    def __init__(self, platform: str, api_key: str | None = None) -> None:
        """Initialize the extractor for a given platform.

        Args:
            platform: "kalshi" or "poly".
            api_key: Optional Anthropic API key (reads from ~/.env if not provided).
        """
        self._platform = platform
        self._client = AnthropicClient(api_key=api_key)

    async def extract_batch(self, markets: Sequence[dict], redis: Redis) -> list[MarketExtraction]:
        """Extract fields for multiple markets with batching, concurrency, and caching.

        Each market dict must have 'id' and 'title'. Optional: 'description', 'tokens'.

        Args:
            markets: Sequence of market dicts.
            redis: Redis connection for caching.

        Returns:
            List of MarketExtraction results (cached + newly extracted).
        """
        cached, uncached = await _load_cached(markets, self._platform, redis)

        if not uncached:
            return cached

        batches = [uncached[i : i + _BATCH_SIZE] for i in range(0, len(uncached), _BATCH_SIZE)]
        logger.info("Extracting %d markets in %d batches (%d concurrent)", len(uncached), len(batches), _CONCURRENT_REQUESTS)

        new_extractions: list[MarketExtraction] = []
        for chunk_start in range(0, len(batches), _CONCURRENT_REQUESTS):
            chunk_end = min(chunk_start + _CONCURRENT_REQUESTS, len(batches))
            chunk = batches[chunk_start:chunk_end]
            chunk_results = await asyncio.gather(*[self._extract_single_batch(b) for b in chunk])
            for result in chunk_results:
                new_extractions.extend(result.values())
            processed = min(chunk_end * _BATCH_SIZE, len(uncached))
            logger.info("Progress: %d/%d markets extracted", processed, len(uncached))

        await _store_extractions(new_extractions, redis)
        logger.info(
            "Extraction complete: %d cached, %d new, %d total", len(cached), len(new_extractions), len(cached) + len(new_extractions)
        )
        return cached + new_extractions

    async def _extract_single_batch(self, batch: list[dict]) -> dict[str, MarketExtraction]:
        """Make a single API call to extract fields for a batch of markets."""
        user_content = build_user_content(batch)
        response_text = await self._client.send_message(EXTRACTION_PROMPT, user_content)
        # Pass original IDs so parser doesn't rely on LLM echoing IDs exactly
        original_ids = [m["id"] for m in batch]
        return parse_batch_response(response_text, self._platform, original_ids)


__all__ = ["MarketExtractor"]
