"""LLM-based field extraction for Polymarket markets.

Extracts structured fields from Poly market titles/descriptions to match Kalshi's schema.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Sequence, cast

import aiohttp
from redis.asyncio import Redis

from ._field_parser import parse_batch_response, parse_llm_response
from ._utils import load_api_key_from_env_file

logger = logging.getLogger(__name__)

_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_MODEL_NAME = "gpt-4o-mini"
_POLY_EXTRACTED_PREFIX = "poly:extracted"
_API_TIMEOUT_SECONDS = 180
_BATCH_SIZE = 20
_CONCURRENT_REQUESTS = 10
_MAX_RETRIES = 5
_INITIAL_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 60.0
_HTTP_RATE_LIMIT = 429
_HTTP_SERVER_ERROR = 500
_MIN_CONCURRENCY = 2

KALSHI_CATEGORIES = (
    "Crypto",
    "Climate and Weather",
    "Economics",
    "Politics",
    "Sports",
    "Entertainment",
    "Science",
    "Technology",
    "Finance",
    "Company",
)


_EXTRACTION_PROMPT_SINGLE = f"""You are a market data analyst. Extract Kalshi-style structured fields from Polymarket market data.

Valid categories (use EXACTLY one of these):
{json.dumps(KALSHI_CATEGORIES)}

Extract these fields:
1. category: From the list above
2. underlying: Short uppercase asset code matching Kalshi format. Examples:
   - Crypto: "BTC", "ETH", "SOL", "XRP", "DOGE"
   - Economics: "FED", "GDP", "CPI", "FOMC"
   - Sports: team abbreviations like "NYK", "LAL", "KC", "BUF"
   - Weather: station codes like "KORD", "KJFK"
   - Other: short descriptive code
3. subject: Short uppercase code identifying the specific entity within the underlying. Examples:
   - For Rotten Tomatoes (RT): movie abbreviation like "MER" (Mercy), "RSH" (Return to Silent Hill)
   - For sports: player or event code like "MAHOMES", "SB"
   - For crypto: same as underlying (e.g., "BTC", "ETH")
   - For economics: specific metric like "RATE", "PCE"
4. floor_strike: Lower bound number, or null if none. For "above $3500" → 3500. For "between $3500 and $3600" → 3500.
5. cap_strike: Upper bound number, or null if none. For "below $3600" → 3600. For "between $3500 and $3600" → 3600.

Return JSON with these exact fields: category (string), underlying (string), subject (string), floor_strike (number or null), cap_strike (number or null)."""

_EXTRACTION_PROMPT_BATCH = f"""You are a market data analyst. Extract Kalshi-style structured fields from multiple Polymarket markets.

Valid categories (use EXACTLY one of these): {json.dumps(KALSHI_CATEGORIES)}

For EACH market, extract:
- category: From the list above (string)
- underlying: Short uppercase asset code (string). Examples:
  - Crypto: "BTC", "ETH", "SOL", "XRP"
  - Economics: "FED", "GDP", "CPI", "FOMC"
  - Sports: "NYK", "LAL", "KC", "BUF"
  - Weather: "KORD", "KJFK"
- subject: Short uppercase code for the specific entity within the underlying (string). Examples:
  - Rotten Tomatoes: movie abbreviation like "MER" (Mercy), "RSH" (Return to Silent Hill)
  - Sports: player or event code
  - Crypto: same as underlying (e.g., "BTC")
- floor_strike: Lower bound number or null. "above $3500" → 3500, "between $3500-$3600" → 3500
- cap_strike: Upper bound number or null. "below $3600" → 3600, "between $3500-$3600" → 3600

Return JSON: {{"markets": [{{"id": "...", "category": "...", "underlying": "...", "subject": "...", "floor_strike": number|null, "cap_strike": number|null}}]}}

IMPORTANT: floor_strike and cap_strike must be numbers or null, never strings."""


@dataclass
class ExtractedFields:
    """Extracted Kalshi-normalized fields from a Poly market."""

    condition_id: str
    category: str
    underlying: str
    subject: str
    floor_strike: float | None
    cap_strike: float | None


def _get_redis_key(condition_id: str) -> str:
    """Generate Redis key for extracted fields."""
    return f"{_POLY_EXTRACTED_PREFIX}:{condition_id}"


def _build_market_text(market: dict) -> str:
    """Build text prompt for a single market."""
    if "condition_id" not in market:
        raise KeyError("condition_id is required")
    condition_id = market["condition_id"]

    if "title" not in market:
        raise KeyError(f"title is required for market {condition_id}")
    title = market["title"]

    if "description" not in market:
        raise KeyError(f"description is required for market {condition_id}")
    description = market["description"][:500]

    if "tokens" not in market:
        raise KeyError(f"tokens is required for market {condition_id}")
    tokens_str = market["tokens"]

    tokens = json.loads(tokens_str) if isinstance(tokens_str, str) else tokens_str
    outcomes = []
    for t in tokens:
        if "outcome" not in t:
            raise KeyError(f"outcome field is required in token: {t}")
        outcomes.append(t["outcome"])

    return f"[ID: {condition_id}]\nTitle: {title}\nDescription: {description}\nOutcomes: {outcomes}"


def _handle_rate_limit(extractor: "FieldExtractor", resp: aiohttp.ClientResponse, backoff: float, attempt: int) -> float:
    """Handle rate limit response and return wait time."""
    extractor._rate_limit_hits += 1
    if extractor._current_concurrency > _MIN_CONCURRENCY:
        extractor._current_concurrency = max(_MIN_CONCURRENCY, extractor._current_concurrency // 2)
        logger.warning("Rate limit hit, reducing concurrency to %d", extractor._current_concurrency)

    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        wait_time = float(retry_after)
    else:
        wait_time = backoff
    logger.warning("Rate limited (429), waiting %.1fs before retry %d/%d", wait_time, attempt + 1, _MAX_RETRIES)
    return wait_time


async def _store_extracted_fields(fields_list: list[ExtractedFields], redis: Redis) -> None:
    """Store extracted fields in Redis."""
    pipe = redis.pipeline()
    for fields in fields_list:
        field_map = _build_field_map(fields)
        redis_key = _get_redis_key(fields.condition_id)
        pipe.hset(redis_key, mapping=field_map)

    await pipe.execute()


def _build_field_map(fields: ExtractedFields) -> dict[str, str]:
    """Build Redis field map from extracted fields."""
    field_map: dict[str, str] = {"category": fields.category, "underlying": fields.underlying, "subject": fields.subject}
    if fields.floor_strike is not None:
        field_map["floor_strike"] = str(fields.floor_strike)
    if fields.cap_strike is not None:
        field_map["cap_strike"] = str(fields.cap_strike)
    return field_map


def _parse_cached_fields(condition_id: str, existing: dict) -> ExtractedFields:
    """Parse cached Redis fields into ExtractedFields."""
    if b"category" not in existing:
        raise KeyError(f"category not found in cached fields for {condition_id}")
    if b"underlying" not in existing:
        raise KeyError(f"underlying not found in cached fields for {condition_id}")

    category = existing[b"category"].decode()
    underlying = existing[b"underlying"].decode()
    subject = existing[b"subject"].decode() if b"subject" in existing and existing[b"subject"] else underlying
    floor_strike = float(existing[b"floor_strike"].decode()) if b"floor_strike" in existing and existing[b"floor_strike"] else None
    cap_strike = float(existing[b"cap_strike"].decode()) if b"cap_strike" in existing and existing[b"cap_strike"] else None

    return ExtractedFields(
        condition_id=condition_id,
        category=category,
        underlying=underlying,
        subject=subject,
        floor_strike=floor_strike,
        cap_strike=cap_strike,
    )


async def _call_openai_api(api_key: str, payload: dict) -> dict:
    """Call OpenAI API with the given payload."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=_API_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(_OPENAI_API_URL, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()


async def _load_batch_cached_fields(markets: Sequence[dict], redis: Redis) -> tuple[list[ExtractedFields], list[dict], int]:
    """Load cached fields for batch processing."""
    results: list[ExtractedFields] = []
    to_extract: list[dict] = []
    cached_count = 0

    for market in markets:
        if "condition_id" not in market:
            logger.warning("Skipping market without condition_id")
            continue
        condition_id = market["condition_id"]
        redis_key = _get_redis_key(condition_id)
        existing = await redis.hgetall(redis_key)

        if existing:
            cached_count += 1
            fields = _parse_cached_fields(condition_id, existing)
            results.append(fields)
        else:
            to_extract.append(market)

    if cached_count > 0:
        logger.info("Cache hits: %d, need to extract: %d", cached_count, len(to_extract))

    return results, to_extract, cached_count


async def _make_api_request(
    session: aiohttp.ClientSession,
    payload: dict,
    headers: dict,
    extractor: "FieldExtractor",
) -> dict:
    """Make API request with retry logic."""
    backoff = _INITIAL_BACKOFF_SECONDS
    for attempt in range(_MAX_RETRIES):
        try:
            async with session.post(_OPENAI_API_URL, json=payload, headers=headers) as resp:
                if resp.status == _HTTP_RATE_LIMIT:
                    wait_time = _handle_rate_limit(extractor, resp, backoff, attempt)
                    await asyncio.sleep(wait_time)
                    backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
                    continue

                if resp.status >= _HTTP_SERVER_ERROR:
                    logger.warning("Server error (%d), waiting %.1fs before retry %d/%d", resp.status, backoff, attempt + 1, _MAX_RETRIES)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
                    continue

                resp.raise_for_status()
                return await resp.json()

        except aiohttp.ClientError as exc:
            logger.warning("API call failed (attempt %d/%d): %s", attempt + 1, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
                continue
            raise

    raise RuntimeError(f"API call failed after {_MAX_RETRIES} retries")


class FieldExtractor:
    """Service for extracting structured fields from Poly markets using LLM."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the field extractor."""
        if api_key:
            self._api_key = api_key
        else:
            loaded_key = load_api_key_from_env_file("OPENAI_API_KEY")
            if not loaded_key:
                raise ValueError("OPENAI_API_KEY not found in ~/.env")
            self._api_key = loaded_key
        self._current_concurrency = _CONCURRENT_REQUESTS
        self._rate_limit_hits = 0
        logger.info("Initialized FieldExtractor with OpenAI API (model: %s)", _MODEL_NAME)

    async def extract_fields(self, condition_id: str, title: str, description: str, tokens: list[dict]) -> ExtractedFields | None:
        """Extract structured fields from a single Poly market."""
        outcomes = []
        for t in tokens:
            if "outcome" not in t:
                raise KeyError(f"outcome field is required in token: {t}")
            outcomes.append(t["outcome"])
        market_text = f"Title: {title}\nDescription: {description}\nOutcomes: {outcomes}"

        payload = {
            "model": _MODEL_NAME,
            "messages": [
                {"role": "system", "content": _EXTRACTION_PROMPT_SINGLE},
                {"role": "user", "content": market_text},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        result = await _call_openai_api(self._api_key, payload)
        response_text = result["choices"][0]["message"]["content"]
        return parse_llm_response(response_text, condition_id, KALSHI_CATEGORIES)

    async def extract_and_store(
        self, condition_id: str, title: str, description: str, tokens: list[dict], redis: Redis
    ) -> ExtractedFields | None:
        """Extract fields and store in Redis if not already present."""
        redis_key = _get_redis_key(condition_id)

        existing = await redis.hgetall(redis_key)
        if existing:
            logger.debug("Using cached extracted fields for %s", condition_id)
            return _parse_cached_fields(condition_id, existing)

        fields = await self.extract_fields(condition_id, title, description, tokens)
        if fields is None:
            return None

        field_map = _build_field_map(fields)
        await redis.hset(redis_key, mapping=field_map)
        logger.info("Stored extracted fields for %s: category=%s, underlying=%s", condition_id, fields.category, fields.underlying)

        return fields

    async def _extract_batch_api_call(self, markets_batch: list[dict], session: aiohttp.ClientSession) -> dict[str, ExtractedFields]:
        """Make a single API call to extract fields for multiple markets."""
        market_texts = [_build_market_text(m) for m in markets_batch]
        user_content = "\n\n---\n\n".join(market_texts)

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {
            "model": _MODEL_NAME,
            "messages": [
                {"role": "system", "content": _EXTRACTION_PROMPT_BATCH},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            result = await _make_api_request(session, payload, headers, self)
            response_text = result["choices"][0]["message"]["content"]
            return parse_batch_response(response_text, KALSHI_CATEGORIES)
        except (RuntimeError, KeyError, json.JSONDecodeError):
            logger.exception("Batch API call failed")
            raise

    async def extract_batch(self, markets: Sequence[dict], redis: Redis) -> list[ExtractedFields]:
        """Extract fields for multiple markets with batching and concurrency."""
        results, to_extract, cached_count = await _load_batch_cached_fields(markets, redis)

        if not to_extract:
            return results

        batches = [to_extract[i : i + _BATCH_SIZE] for i in range(0, len(to_extract), _BATCH_SIZE)]
        logger.info("Extracting %d markets in %d batches (%d concurrent)", len(to_extract), len(batches), self._current_concurrency)

        timeout = aiohttp.ClientTimeout(total=_API_TIMEOUT_SECONDS)
        batch_results: list[dict[str, ExtractedFields]] = []

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for chunk_start in range(0, len(batches), self._current_concurrency):
                chunk_end = min(chunk_start + self._current_concurrency, len(batches))
                chunk = batches[chunk_start:chunk_end]

                chunk_results = await asyncio.gather(*[self._extract_batch_api_call(b, session) for b in chunk])
                batch_results.extend(chunk_results)

                processed = min(chunk_end * _BATCH_SIZE, len(to_extract))
                logger.info("Progress: %d/%d markets extracted (concurrency: %d)", processed, len(to_extract), self._current_concurrency)

        extracted_fields_list = []
        for batch_result in batch_results:
            for fields in batch_result.values():
                results.append(fields)
                extracted_fields_list.append(fields)

        await _store_extracted_fields(extracted_fields_list, redis)

        logger.info(
            "Field extraction complete: %d cached, %d newly extracted, %d total", cached_count, len(extracted_fields_list), len(results)
        )
        return results


__all__ = ["ExtractedFields", "FieldExtractor", "KALSHI_CATEGORIES"]
