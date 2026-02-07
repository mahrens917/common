"""Market extraction services with Redis caching."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from ..redis_protocol.typing import ensure_awaitable

if TYPE_CHECKING:
    pass

from ._extractor_helpers import (
    extract_kalshi_batch_with_retry,
    extract_poly_batch_with_retry,
    get_batch_size,
    get_concurrent_requests,
    get_min_underlyings_for_dedup,
    get_redis_key,
    get_ttl,
    load_kalshi_cached,
    load_poly_cached_batch,
)
from ._response_parser import (
    parse_expiry_alignment_response,
    parse_kalshi_dedup_response,
)
from .client import AnthropicClient
from .models import MarketExtraction
from .prompts import (
    build_expiry_alignment_prompt,
    build_expiry_alignment_user_content,
    build_kalshi_dedup_prompt,
)

logger = logging.getLogger(__name__)

_REDIS_PREFIX_DEDUP = "crossarb:dedup"
_REDIS_PREFIX_EXPIRY_ALIGN = "crossarb:expiry_align"


class KalshiUnderlyingExtractor:
    """Extract underlyings from Kalshi markets with batching and caching."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the extractor."""
        self._client = AnthropicClient(model="claude-haiku-4-5", max_tokens=4096, api_key=api_key)

    @property
    def client(self) -> AnthropicClient:
        """Access the underlying Anthropic client for usage stats."""
        return self._client

    async def _load_cached_underlyings(
        self,
        markets: list[dict],
        redis: Redis,
    ) -> tuple[dict[str, str], set[str]]:
        """Load cached underlyings from Redis."""
        results: dict[str, str] = {}
        accumulated: set[str] = set()
        for market in markets:
            market_id = market["id"]
            cached = await load_kalshi_cached(market_id, redis)
            if cached:
                results[market_id] = cached
                accumulated.add(cached)
        return results, accumulated

    async def _process_extraction_chunk(
        self,
        chunk: list[list[dict]],
        accumulated_underlyings: set[str],
        results: dict[str, str],
        redis: Redis,
    ) -> None:
        """Process a chunk of batches for extraction."""
        existing = list(accumulated_underlyings)
        tasks = [extract_kalshi_batch_with_retry(self._client, batch, existing, redis) for batch in chunk]
        chunk_results = await asyncio.gather(*tasks)
        for batch_results in chunk_results:
            for market_id, underlying in batch_results.items():
                results[market_id] = underlying
                accumulated_underlyings.add(underlying)

    async def extract_underlyings(
        self,
        markets: list[dict],
        redis: Redis,
    ) -> dict[str, str]:
        """Extract underlyings for Kalshi markets with batching."""
        results, accumulated_underlyings = await self._load_cached_underlyings(markets, redis)

        uncached = [m for m in markets if m["id"] not in results]
        if not uncached:
            logger.info("All %d Kalshi markets cached", len(markets))
            return results

        logger.info("Extracting underlyings for %d uncached Kalshi markets", len(uncached))

        batch_size = get_batch_size()
        concurrent = get_concurrent_requests()
        batches = [uncached[i : i + batch_size] for i in range(0, len(uncached), batch_size)]

        for chunk_start in range(0, len(batches), concurrent):
            chunk_end = min(chunk_start + concurrent, len(batches))
            chunk = batches[chunk_start:chunk_end]
            await self._process_extraction_chunk(chunk, accumulated_underlyings, results, redis)

            processed = min(chunk_end * batch_size, len(uncached))
            logger.info(
                "Progress: %d/%d Kalshi markets extracted (total: $%.4f)",
                processed,
                len(uncached),
                self._client.get_cost(),
            )

        logger.info(
            "Kalshi extraction complete: %d total (total: $%.4f)",
            len(results),
            self._client.get_cost(),
        )
        return results


class KalshiDedupExtractor:
    """Deduplicate underlyings within categories."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the extractor."""
        self._client = AnthropicClient(model="claude-haiku-4-5", max_tokens=4096, api_key=api_key)

    @property
    def client(self) -> AnthropicClient:
        """Access the underlying Anthropic client for usage stats."""
        return self._client

    async def dedup_underlyings(
        self,
        underlyings_by_category: dict[str, set[str]],
        redis: Redis,
    ) -> dict[str, str]:
        """Deduplicate underlyings across all categories."""
        import json as json_module

        all_mappings: dict[str, str] = {}
        uncached_categories: list[tuple[str, list[str], str]] = []
        min_underlyings = get_min_underlyings_for_dedup()

        for category, underlyings in underlyings_by_category.items():
            if len(underlyings) < min_underlyings:
                continue

            underlyings_hash = hash(tuple(sorted(underlyings)))
            cache_key = f"{_REDIS_PREFIX_DEDUP}:{category}:{underlyings_hash}"
            cached = await redis.get(cache_key)
            if cached:
                cached_mapping = json_module.loads(cached)
                all_mappings.update(cached_mapping)
                logger.info("Loaded cached dedup mapping for %s", category)
            else:
                uncached_categories.append((category, list(underlyings), cache_key))

        if not uncached_categories:
            return all_mappings

        logger.info("Deduplicating %d categories", len(uncached_categories))
        tasks = [self._dedup_category_with_cache(cat, underlyings, cache_key, redis) for cat, underlyings, cache_key in uncached_categories]
        results = await asyncio.gather(*tasks)

        for mapping in results:
            all_mappings.update(mapping)

        logger.info("Dedup complete: %d aliases found (total: $%.4f)", len(all_mappings), self._client.get_cost())
        return all_mappings

    async def _dedup_category_with_cache(
        self,
        category: str,
        underlyings: list[str],
        cache_key: str,
        redis: Redis,
    ) -> dict[str, str]:
        """Run dedup for a single category and cache result."""
        import json as json_module

        mapping = await self._dedup_category(category, underlyings)
        await redis.set(cache_key, json_module.dumps(mapping), ex=get_ttl())
        if mapping:
            logger.info("Deduped %s: found %d aliases", category, len(mapping))
        return mapping

    async def _dedup_category(self, category: str, underlyings: list[str]) -> dict[str, str]:
        """Run dedup for a single category."""
        prompt = build_kalshi_dedup_prompt(category, underlyings)
        response = await self._client.send_message(prompt, "Please identify any duplicates.")
        return parse_kalshi_dedup_response(response, original_underlyings=set(underlyings))


class PolyExtractor:
    """Extract fields from Poly markets with validation and retry."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the extractor."""
        self._client = AnthropicClient(model="claude-haiku-4-5", max_tokens=4096, api_key=api_key)

    @property
    def client(self) -> AnthropicClient:
        """Access the underlying Anthropic client for usage stats."""
        return self._client

    async def extract_batch(
        self,
        markets: list[dict],
        valid_categories: set[str],
        valid_underlyings: set[str],
        redis: Redis,
    ) -> list[MarketExtraction]:
        """Extract fields for Poly markets with batching and retry."""
        results: list[MarketExtraction] = []

        cached, uncached = await load_poly_cached_batch(markets, redis)
        results.extend(cached)

        if not uncached:
            logger.info("All %d Poly markets cached", len(markets))
            return results

        logger.info("Extracting %d uncached Poly markets", len(uncached))

        batch_size = get_batch_size()
        concurrent = get_concurrent_requests()
        batches = [uncached[i : i + batch_size] for i in range(0, len(uncached), batch_size)]

        for chunk_start in range(0, len(batches), concurrent):
            chunk_end = min(chunk_start + concurrent, len(batches))
            chunk = batches[chunk_start:chunk_end]

            tasks = [extract_poly_batch_with_retry(self._client, batch, valid_categories, valid_underlyings, redis) for batch in chunk]
            chunk_results = await asyncio.gather(*tasks)

            for batch_results in chunk_results:
                results.extend(batch_results)

            processed = min(chunk_end * batch_size, len(uncached))
            logger.info(
                "Progress: %d/%d Poly markets extracted (total: $%.4f)",
                processed,
                len(uncached),
                self._client.get_cost(),
            )

        logger.info(
            "Poly extraction complete: %d cached, %d new (total: $%.4f)",
            len(cached),
            len(results) - len(cached),
            self._client.get_cost(),
        )
        return results


class ExpiryAligner:
    """Align Poly expiry with Kalshi expiry for near-miss pairs."""

    def __init__(self, redis: Redis) -> None:
        self._client = AnthropicClient(model="claude-haiku-4-5", max_tokens=4096)
        self._redis = redis

    @property
    def client(self) -> AnthropicClient:
        """Get the underlying Anthropic client for usage stats."""
        return self._client

    @staticmethod
    def _get_cache_key(kalshi_id: str, poly_id: str) -> str:
        """Generate cache key for expiry alignment."""
        return f"{_REDIS_PREFIX_EXPIRY_ALIGN}:{kalshi_id}:{poly_id}"

    async def _get_cached(self, kalshi_id: str, poly_id: str) -> tuple[bool, str | None]:
        """Check cache for alignment result."""
        key = self._get_cache_key(kalshi_id, poly_id)
        data = await ensure_awaitable(self._redis.hgetall(key))
        if not data:
            return False, None

        if data.get("status") == "no_match":
            return True, None

        return True, data.get("aligned_expiry")

    async def _store_cached(self, kalshi_id: str, poly_id: str, aligned_expiry: str | None) -> None:
        """Store alignment result in cache."""
        key = self._get_cache_key(kalshi_id, poly_id)
        if aligned_expiry:
            await ensure_awaitable(self._redis.hset(key, mapping={"aligned_expiry": aligned_expiry}))
        else:
            await ensure_awaitable(self._redis.hset(key, mapping={"status": "no_match"}))
        await self._redis.expire(key, get_ttl())

    async def align_expiry(
        self,
        kalshi_id: str,
        kalshi_title: str,
        kalshi_expiry: str,
        poly_id: str,
        poly_title: str,
        poly_expiry: str,
        context: dict[str, str] | None = None,
    ) -> str | None:
        """Determine if markets are the same event and return aligned expiry."""
        found, cached_result = await self._get_cached(kalshi_id, poly_id)
        if found:
            return cached_result

        underlying = context.get("underlying") if context else None
        strike_info = context.get("strike_info") if context else None

        prompt = build_expiry_alignment_prompt()
        user_content = build_expiry_alignment_user_content(
            kalshi_title,
            kalshi_expiry,
            poly_title,
            poly_expiry,
            underlying,
            strike_info,
        )

        response = await self._client.send_message(prompt, user_content)
        result = parse_expiry_alignment_response(response)

        await self._store_cached(kalshi_id, poly_id, result)

        return result

    async def align_batch(
        self,
        pairs: list[tuple[str, str, str, str, str, str, dict[str, str] | None]],
    ) -> list[str | None]:
        """Align expiries for multiple pairs with limited concurrency."""
        results: list[str | None] = []
        concurrent = get_concurrent_requests()

        for chunk_start in range(0, len(pairs), concurrent):
            chunk = pairs[chunk_start : chunk_start + concurrent]
            tasks = [
                self.align_expiry(k_id, k_title, k_expiry, p_id, p_title, p_expiry, ctx)
                for k_id, k_title, k_expiry, p_id, p_title, p_expiry, ctx in chunk
            ]
            chunk_results = await asyncio.gather(*tasks)
            results.extend(chunk_results)

            if chunk_start + concurrent < len(pairs):
                logger.info(
                    "Expiry alignment progress: %d/%d (total: $%.4f)",
                    min(chunk_start + concurrent, len(pairs)),
                    len(pairs),
                    self._client.get_cost(),
                )

        return results


__all__ = [
    "KalshiUnderlyingExtractor",
    "KalshiDedupExtractor",
    "PolyExtractor",
    "ExpiryAligner",
    "get_redis_key",
    "get_ttl",
]
