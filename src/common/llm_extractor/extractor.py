"""Market extraction services with Redis caching."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from ..redis_protocol.typing import ensure_awaitable

if TYPE_CHECKING:
    pass

from ._response_parser import (
    ExtraDataInResponse,
    parse_expiry_alignment_response,
    parse_kalshi_dedup_response,
    parse_kalshi_underlying_batch_response,
    parse_kalshi_underlying_response,
    parse_poly_batch_response,
    parse_poly_extraction_response,
)
from .client import AnthropicClient
from .models import MarketExtraction
from .prompts import (
    build_expiry_alignment_prompt,
    build_expiry_alignment_user_content,
    build_kalshi_dedup_prompt,
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
_REDIS_PREFIX_DEDUP = "crossarb:dedup"
_BATCH_SIZE = 10
_CONCURRENT_REQUESTS = 5


def _get_redis_key(market_id: str, platform: str) -> str:
    """Generate Redis key for extracted fields."""
    if platform == "kalshi":
        return f"{_REDIS_PREFIX_KALSHI}:{market_id}"
    return f"{_REDIS_PREFIX_POLY}:{market_id}"


def _get_ttl() -> int:
    """Return TTL in seconds."""
    return _TTL_SECONDS


class KalshiUnderlyingExtractor:
    """Extract underlyings from Kalshi markets with batching and caching."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the extractor.

        Args:
            api_key: Optional Anthropic API key (reads from ~/.env if not provided).
        """
        self._client = AnthropicClient(api_key=api_key)

    @property
    def client(self) -> AnthropicClient:
        """Access the underlying Anthropic client for usage stats."""
        return self._client

    async def extract_underlyings(
        self,
        markets: list[dict],
        redis: Redis,
    ) -> dict[str, str]:
        """Extract underlyings for Kalshi markets with batching.

        Args:
            markets: List of market dicts with 'id', 'title', 'rules_primary', 'category'.
            redis: Redis connection for caching.

        Returns:
            Dict mapping market_id -> underlying.
        """
        results: dict[str, str] = {}
        accumulated_underlyings: set[str] = set()

        # Load cached extractions first
        for market in markets:
            market_id = market["id"]
            cached = await self._load_cached(market_id, redis)
            if cached:
                results[market_id] = cached
                accumulated_underlyings.add(cached)

        uncached = [m for m in markets if m["id"] not in results]
        if not uncached:
            logger.info("All %d Kalshi markets cached", len(markets))
            return results

        logger.info("Extracting underlyings for %d uncached Kalshi markets", len(uncached))

        # Process in batches with concurrency
        batches = [uncached[i : i + _BATCH_SIZE] for i in range(0, len(uncached), _BATCH_SIZE)]

        for chunk_start in range(0, len(batches), _CONCURRENT_REQUESTS):
            chunk_end = min(chunk_start + _CONCURRENT_REQUESTS, len(batches))
            chunk = batches[chunk_start:chunk_end]

            # All batches in this chunk share the same existing underlyings
            existing = list(accumulated_underlyings)
            tasks = [self._extract_batch_with_retry(batch, existing, redis) for batch in chunk]
            chunk_results = await asyncio.gather(*tasks)

            # Merge results and accumulate new underlyings
            for batch_results in chunk_results:
                for market_id, underlying in batch_results.items():
                    results[market_id] = underlying
                    accumulated_underlyings.add(underlying)

            processed = min(chunk_end * _BATCH_SIZE, len(uncached))
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

    async def _extract_batch_with_retry(
        self,
        batch: list[dict],
        existing_underlyings: list[str],
        redis: Redis,
    ) -> dict[str, str]:
        """Extract underlyings for a batch with retry for failed items."""
        prompt = build_kalshi_underlying_batch_prompt(existing_underlyings)
        user_content = build_kalshi_underlying_batch_user_content(batch)
        original_ids = [m["id"] for m in batch]

        # Use batch prefill to force {"markets": [...]} structure
        # Retry once if LLM adds extra data after JSON
        for attempt in range(2):
            response = await self._client.send_message(prompt, user_content, json_prefill='{"markets": [')
            try:
                results, failed_ids = parse_kalshi_underlying_batch_response(response, original_ids)
                break
            except ExtraDataInResponse as e:
                if attempt == 0:
                    logger.debug("Extra data in Kalshi batch response, retrying: %s", e.extra_text[:100])
                    continue
                # Second attempt also had extra data, fall back to individual extraction
                logger.warning("Extra data persisted after retry, falling back to individual extraction")
                results = {}
                failed_ids = original_ids

        # Retry failed items individually
        if failed_ids:
            logger.debug("Retrying %d failed Kalshi extractions", len(failed_ids))
            failed_markets = [m for m in batch if m["id"] in failed_ids]
            for market in failed_markets:
                underlying = await self._extract_single(market, existing_underlyings)
                if underlying:
                    results[market["id"]] = underlying

        # Store successful extractions in cache
        await self._store_cached_batch(results, redis)

        return results

    async def _extract_single(self, market: dict, existing_underlyings: list[str]) -> str | None:
        """Extract underlying for a single market (used for retries)."""
        prompt = build_kalshi_underlying_prompt(existing_underlyings)
        user_content = build_kalshi_underlying_user_content(
            title=market.get("title", ""),
            rules_primary=market.get("rules_primary", ""),
            category=market.get("category", ""),
        )
        response = await self._client.send_message(prompt, user_content)
        return parse_kalshi_underlying_response(response)

    async def _load_cached(self, market_id: str, redis: Redis) -> str | None:
        """Load cached underlying from Redis."""
        key = _get_redis_key(market_id, "kalshi")
        data = await ensure_awaitable(redis.hgetall(key))
        if data and "underlying" in data:
            return data["underlying"]
        return None

    async def _store_cached_batch(self, results: dict[str, str], redis: Redis) -> None:
        """Store batch of underlyings in Redis cache."""
        if not results:
            return

        pipe = redis.pipeline()
        for market_id, underlying in results.items():
            key = _get_redis_key(market_id, "kalshi")
            pipe.hset(key, mapping={"underlying": underlying})
            pipe.expire(key, _get_ttl())

        await pipe.execute()


class KalshiDedupExtractor:
    """Deduplicate underlyings within categories."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the extractor.

        Args:
            api_key: Optional Anthropic API key.
        """
        self._client = AnthropicClient(api_key=api_key)

    @property
    def client(self) -> AnthropicClient:
        """Access the underlying Anthropic client for usage stats."""
        return self._client

    async def dedup_underlyings(
        self,
        underlyings_by_category: dict[str, set[str]],
        redis: Redis,
    ) -> dict[str, str]:
        """Deduplicate underlyings across all categories.

        Args:
            underlyings_by_category: Dict mapping category -> set of underlyings.
            redis: Redis connection for caching.

        Returns:
            Dict mapping alias -> canonical for all duplicates found.
        """
        import json as json_module

        all_mappings: dict[str, str] = {}
        uncached_categories: list[tuple[str, list[str]]] = []

        # Check cache for all categories first
        for category, underlyings in underlyings_by_category.items():
            if len(underlyings) < 2:
                continue

            # Include hash of underlyings in cache key so cache invalidates when underlyings change
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

        # Process uncached categories concurrently
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
        # Always cache result (even empty) to avoid re-running LLM
        await redis.set(cache_key, json_module.dumps(mapping), ex=_get_ttl())
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
        """Initialize the extractor.

        Args:
            api_key: Optional Anthropic API key.
        """
        self._client = AnthropicClient(api_key=api_key)

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
        """Extract fields for Poly markets with batching and retry.

        Args:
            markets: List of market dicts with 'id', 'title', optional 'description'.
            valid_categories: Set of valid categories from Kalshi.
            valid_underlyings: Set of valid underlyings from Kalshi.
            redis: Redis connection for caching.

        Returns:
            List of valid MarketExtraction results.
        """
        results: list[MarketExtraction] = []

        # Load cached extractions first
        cached, uncached = await self._load_cached_batch(markets, redis)
        results.extend(cached)

        if not uncached:
            logger.info("All %d Poly markets cached", len(markets))
            return results

        logger.info("Extracting %d uncached Poly markets", len(uncached))

        # Process in batches
        batches = [uncached[i : i + _BATCH_SIZE] for i in range(0, len(uncached), _BATCH_SIZE)]

        for chunk_start in range(0, len(batches), _CONCURRENT_REQUESTS):
            chunk_end = min(chunk_start + _CONCURRENT_REQUESTS, len(batches))
            chunk = batches[chunk_start:chunk_end]

            tasks = [self._extract_batch_with_retry(batch, valid_categories, valid_underlyings, redis) for batch in chunk]
            chunk_results = await asyncio.gather(*tasks)

            for batch_results in chunk_results:
                results.extend(batch_results)

            processed = min(chunk_end * _BATCH_SIZE, len(uncached))
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

    async def _extract_batch_with_retry(
        self,
        batch: list[dict],
        valid_categories: set[str],
        valid_underlyings: set[str],
        redis: Redis,
    ) -> list[MarketExtraction]:
        """Extract a batch with retry for failed items."""
        prompt = build_poly_prompt(list(valid_categories), list(valid_underlyings))
        user_content = build_poly_batch_user_content(batch)
        original_ids = [m["id"] for m in batch]

        # Use batch prefill to force {"markets": [...]} structure
        # Retry once if LLM adds extra data after JSON
        for attempt in range(2):
            response = await self._client.send_message(prompt, user_content, json_prefill='{"markets": [')
            try:
                extractions, failed_ids = parse_poly_batch_response(response, valid_categories, valid_underlyings, original_ids)
                break
            except ExtraDataInResponse as e:
                if attempt == 0:
                    logger.debug("Extra data in Poly batch response, retrying: %s", e.extra_text[:100])
                    continue
                # Second attempt also had extra data, fall back to individual extraction
                logger.warning("Extra data persisted after retry, falling back to individual extraction")
                extractions = {}
                failed_ids = original_ids

        results = list(extractions.values())
        no_match_ids: list[str] = []

        # Retry failed items individually
        if failed_ids:
            logger.debug("Retrying %d failed Poly extractions", len(failed_ids))
            failed_markets = [m for m in batch if m["id"] in failed_ids]
            for market in failed_markets:
                extraction = await self._extract_single_with_retry(market, valid_categories, valid_underlyings)
                if extraction:
                    results.append(extraction)
                else:
                    no_match_ids.append(market["id"])

        # Store successful extractions in cache
        await self._store_cached_batch(results, redis)

        # Cache failed extractions so we don't retry them
        if no_match_ids:
            await self._store_no_match_batch(no_match_ids, redis)

        return results

    async def _extract_single_with_retry(
        self,
        market: dict,
        valid_categories: set[str],
        valid_underlyings: set[str],
    ) -> MarketExtraction | None:
        """Extract single market with one retry."""
        prompt = build_poly_prompt(list(valid_categories), list(valid_underlyings))
        user_content = build_poly_user_content(
            title=market.get("title", ""),
            description=market.get("description", ""),
        )

        # First attempt
        response = await self._client.send_message(prompt, user_content)
        extraction, error = parse_poly_extraction_response(response, market["id"], valid_categories, valid_underlyings)
        if extraction:
            return extraction

        # Debug level since many Poly markets don't match Kalshi coverage
        logger.debug("First attempt failed for %s: %s, retrying", market["id"], error)

        # Retry once
        response = await self._client.send_message(prompt, user_content)
        extraction, error = parse_poly_extraction_response(response, market["id"], valid_categories, valid_underlyings)
        if extraction:
            return extraction

        logger.debug("Retry failed for %s: %s, skipping", market["id"], error)
        return None

    async def _load_cached_batch(
        self,
        markets: list[dict],
        redis: Redis,
    ) -> tuple[list[MarketExtraction], list[dict]]:
        """Load cached extractions from Redis.

        Returns:
            Tuple of (cached extractions, uncached markets).
        """
        cached: list[MarketExtraction] = []
        uncached: list[dict] = []
        skipped_no_match = 0

        for market in markets:
            market_id = market["id"]
            key = _get_redis_key(market_id, "poly")
            data = await ensure_awaitable(redis.hgetall(key))

            if data:
                # Check if this was marked as no match
                if data.get("status") == "no_match":
                    # Skip - already tried and failed, don't retry
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

    async def _store_cached_batch(self, extractions: list[MarketExtraction], redis: Redis) -> None:
        """Store extractions in Redis cache."""
        if not extractions:
            return

        pipe = redis.pipeline()
        for extraction in extractions:
            key = _get_redis_key(extraction.market_id, "poly")
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
            pipe.expire(key, _get_ttl())

        await pipe.execute()

    async def _store_no_match_batch(self, market_ids: list[str], redis: Redis) -> None:
        """Store no-match markers in Redis cache so we don't retry these markets."""
        if not market_ids:
            return

        pipe = redis.pipeline()
        for market_id in market_ids:
            key = _get_redis_key(market_id, "poly")
            pipe.hset(key, mapping={"status": "no_match"})
            pipe.expire(key, _get_ttl())

        await pipe.execute()
        logger.debug("Cached %d no-match Poly markets", len(market_ids))


class ExpiryAligner:
    """Align Poly expiry with Kalshi expiry for near-miss pairs.

    Used in phase 2 to determine if markets with matching category/underlying/strikes
    but different expiries are actually the same event.
    """

    def __init__(self) -> None:
        self._client = AnthropicClient()

    @property
    def client(self) -> AnthropicClient:
        """Get the underlying Anthropic client for usage stats."""
        return self._client

    async def align_expiry(
        self,
        kalshi_title: str,
        kalshi_expiry: str,
        poly_title: str,
        poly_expiry: str,
    ) -> str | None:
        """Determine if markets are the same event and return aligned expiry.

        Args:
            kalshi_title: Kalshi market title.
            kalshi_expiry: Kalshi expiry in ISO format.
            poly_title: Poly market title.
            poly_expiry: Poly API expiry in ISO format.

        Returns:
            Aligned event_date ISO string if same event, None if different events.
        """
        prompt = build_expiry_alignment_prompt()
        user_content = build_expiry_alignment_user_content(
            kalshi_title, kalshi_expiry, poly_title, poly_expiry
        )

        response = await self._client.send_message(prompt, user_content)
        return parse_expiry_alignment_response(response)

    async def align_batch(
        self,
        pairs: list[tuple[str, str, str, str]],
    ) -> list[str | None]:
        """Align expiries for multiple pairs concurrently.

        Args:
            pairs: List of (kalshi_title, kalshi_expiry, poly_title, poly_expiry) tuples.

        Returns:
            List of aligned event_date strings or None for each pair.
        """
        tasks = [
            self.align_expiry(k_title, k_expiry, p_title, p_expiry)
            for k_title, k_expiry, p_title, p_expiry in pairs
        ]
        return await asyncio.gather(*tasks)


__all__ = [
    "KalshiUnderlyingExtractor",
    "KalshiDedupExtractor",
    "PolyExtractor",
    "ExpiryAligner",
    "_get_redis_key",
    "_get_ttl",
]
