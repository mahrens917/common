"""Market extraction services with Redis caching."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

if TYPE_CHECKING:
    pass

from ._response_parser import (
    parse_kalshi_dedup_response,
    parse_kalshi_underlying_response,
    parse_poly_batch_response,
    parse_poly_extraction_response,
)
from .client import AnthropicClient
from .models import MarketExtraction
from .prompts import (
    build_kalshi_dedup_prompt,
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
    """Extract underlyings from Kalshi markets one at a time with caching."""

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
        """Extract underlyings for Kalshi markets one at a time.

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

        for i, market in enumerate(uncached):
            market_id = market["id"]
            underlying = await self._extract_single(market, list(accumulated_underlyings))

            if underlying:
                results[market_id] = underlying
                accumulated_underlyings.add(underlying)
                await self._store_cached(market_id, underlying, redis)

            if (i + 1) % 50 == 0:
                logger.info("Progress: %d/%d Kalshi markets extracted", i + 1, len(uncached))

        logger.info("Kalshi extraction complete: %d total", len(results))
        return results

    async def _extract_single(self, market: dict, existing_underlyings: list[str]) -> str | None:
        """Extract underlying for a single market."""
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
        data = await redis.hgetall(key)
        if data and "underlying" in data:
            return data["underlying"]
        return None

    async def _store_cached(self, market_id: str, underlying: str, redis: Redis) -> None:
        """Store underlying in Redis cache."""
        key = _get_redis_key(market_id, "kalshi")
        await redis.hset(key, mapping={"underlying": underlying})
        await redis.expire(key, _get_ttl())


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
        all_mappings: dict[str, str] = {}

        for category, underlyings in underlyings_by_category.items():
            if len(underlyings) < 2:
                continue

            # Check cache first
            cache_key = f"{_REDIS_PREFIX_DEDUP}:{category}"
            cached = await redis.get(cache_key)
            if cached:
                import json

                try:
                    cached_mapping = json.loads(cached)
                    all_mappings.update(cached_mapping)
                    logger.info("Loaded cached dedup mapping for %s", category)
                    continue
                except (ValueError, TypeError):
                    pass

            # Run dedup for this category
            mapping = await self._dedup_category(category, list(underlyings))
            if mapping:
                all_mappings.update(mapping)
                # Cache the result
                import json

                await redis.set(cache_key, json.dumps(mapping), ex=_get_ttl())
                logger.info("Deduped %s: found %d aliases", category, len(mapping))

        return all_mappings

    async def _dedup_category(self, category: str, underlyings: list[str]) -> dict[str, str]:
        """Run dedup for a single category."""
        prompt = build_kalshi_dedup_prompt(category, underlyings)
        response = await self._client.send_message(prompt, "Please identify any duplicates.")
        return parse_kalshi_dedup_response(response)


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

            tasks = [
                self._extract_batch_with_retry(batch, valid_categories, valid_underlyings, redis) for batch in chunk
            ]
            chunk_results = await asyncio.gather(*tasks)

            for batch_results in chunk_results:
                results.extend(batch_results)

            processed = min(chunk_end * _BATCH_SIZE, len(uncached))
            logger.info("Progress: %d/%d Poly markets extracted", processed, len(uncached))

        logger.info("Poly extraction complete: %d cached, %d new", len(cached), len(results) - len(cached))
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

        response = await self._client.send_message(prompt, user_content)
        extractions, failed_ids = parse_poly_batch_response(
            response, valid_categories, valid_underlyings, original_ids
        )

        results = list(extractions.values())

        # Retry failed items individually
        if failed_ids:
            logger.info("Retrying %d failed Poly extractions", len(failed_ids))
            failed_markets = [m for m in batch if m["id"] in failed_ids]
            for market in failed_markets:
                extraction = await self._extract_single_with_retry(
                    market, valid_categories, valid_underlyings
                )
                if extraction:
                    results.append(extraction)

        # Store successful extractions in cache
        await self._store_cached_batch(results, redis)

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
        extraction, error = parse_poly_extraction_response(
            response, market["id"], valid_categories, valid_underlyings
        )
        if extraction:
            return extraction

        logger.warning("First attempt failed for %s: %s, retrying", market["id"], error)

        # Retry once
        response = await self._client.send_message(prompt, user_content)
        extraction, error = parse_poly_extraction_response(
            response, market["id"], valid_categories, valid_underlyings
        )
        if extraction:
            return extraction

        logger.warning("Retry failed for %s: %s, skipping", market["id"], error)
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

        for market in markets:
            market_id = market["id"]
            key = _get_redis_key(market_id, "poly")
            data = await redis.hgetall(key)

            if data and "category" in data and "underlying" in data:
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
            else:
                uncached.append(market)

        if cached:
            logger.info("Poly cache hits: %d, need to extract: %d", len(cached), len(uncached))

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


__all__ = [
    "KalshiUnderlyingExtractor",
    "KalshiDedupExtractor",
    "PolyExtractor",
    "_get_redis_key",
    "_get_ttl",
]
