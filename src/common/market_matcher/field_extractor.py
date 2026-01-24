"""LLM-based field extraction for Polymarket markets.

Extracts structured fields from Poly market titles/descriptions to match Kalshi's schema.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

import aiohttp

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_MODEL_NAME = "gpt-4o-mini"
_ENV_FILE_PATH = Path.home() / ".env"
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
3. floor_strike: Lower bound number, or null if none. For "above $3500" → 3500. For "between $3500 and $3600" → 3500.
4. cap_strike: Upper bound number, or null if none. For "below $3600" → 3600. For "between $3500 and $3600" → 3600.

Return JSON with these exact fields: category (string), underlying (string), floor_strike (number or null), cap_strike (number or null)."""

_EXTRACTION_PROMPT_BATCH = f"""You are a market data analyst. Extract Kalshi-style structured fields from multiple Polymarket markets.

Valid categories (use EXACTLY one of these): {json.dumps(KALSHI_CATEGORIES)}

For EACH market, extract:
- category: From the list above (string)
- underlying: Short uppercase asset code (string). Examples:
  - Crypto: "BTC", "ETH", "SOL", "XRP"
  - Economics: "FED", "GDP", "CPI", "FOMC"
  - Sports: "NYK", "LAL", "KC", "BUF"
  - Weather: "KORD", "KJFK"
- floor_strike: Lower bound number or null. "above $3500" → 3500, "between $3500-$3600" → 3500
- cap_strike: Upper bound number or null. "below $3600" → 3600, "between $3500-$3600" → 3600

Return JSON: {{"markets": [{{"id": "...", "category": "...", "underlying": "...", "floor_strike": number|null, "cap_strike": number|null}}]}}

IMPORTANT: floor_strike and cap_strike must be numbers or null, never strings."""


@dataclass
class ExtractedFields:
    """Extracted Kalshi-normalized fields from a Poly market."""

    condition_id: str
    category: str
    underlying: str
    floor_strike: float | None
    cap_strike: float | None


def _load_api_key_from_env_file() -> str | None:
    """Load OPENAI_API_KEY from ~/.env file."""
    if not _ENV_FILE_PATH.exists():
        return None
    for line in _ENV_FILE_PATH.read_text().splitlines():
        line = line.strip()
        if line.startswith("OPENAI_API_KEY="):
            value = line.split("=", 1)[1].strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            return value
    return None


def _get_redis_key(condition_id: str) -> str:
    """Generate Redis key for extracted fields."""
    return f"{_POLY_EXTRACTED_PREFIX}:{condition_id}"


def _parse_strike_value(value: object) -> float | None:
    """Parse a strike value to float, handling strings and nulls."""
    if value is None:
        return None
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_llm_response(response_text: str, condition_id: str) -> ExtractedFields | None:
    """Parse LLM response into ExtractedFields."""
    try:
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        data = json.loads(text)

        category = data.get("category", "")
        if category not in KALSHI_CATEGORIES:
            logger.warning("Invalid category '%s' for %s", category, condition_id)
            category = "Entertainment"

        underlying = data.get("underlying", "")
        if not isinstance(underlying, str) or not underlying:
            logger.warning("Invalid underlying for %s: %s", condition_id, underlying)
            return None

        floor_strike = _parse_strike_value(data.get("floor_strike"))
        cap_strike = _parse_strike_value(data.get("cap_strike"))

        return ExtractedFields(
            condition_id=condition_id,
            category=category,
            underlying=underlying.upper(),
            floor_strike=floor_strike,
            cap_strike=cap_strike,
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        logger.exception("Failed to parse LLM response for %s", condition_id)
        raise


def _build_market_text(market: dict) -> str:
    """Build text prompt for a single market."""
    condition_id = market.get("condition_id", "")
    title = market.get("title", "")
    description = market.get("description", "")[:500]
    tokens_str = market.get("tokens", "[]")
    try:
        tokens = json.loads(tokens_str) if isinstance(tokens_str, str) else tokens_str
        outcomes = [t.get("outcome", "") for t in tokens]
    except json.JSONDecodeError:
        logger.exception("Failed to parse tokens for %s", condition_id)
        raise
    return f"[ID: {condition_id}]\nTitle: {title}\nDescription: {description}\nOutcomes: {outcomes}"


def _handle_rate_limit(extractor: "FieldExtractor", resp: aiohttp.ClientResponse, backoff: float, attempt: int) -> float:
    """Handle rate limit response and return wait time."""
    extractor._rate_limit_hits += 1
    if extractor._current_concurrency > _MIN_CONCURRENCY:
        extractor._current_concurrency = max(_MIN_CONCURRENCY, extractor._current_concurrency // 2)
        logger.warning("Rate limit hit, reducing concurrency to %d", extractor._current_concurrency)

    retry_after = resp.headers.get("Retry-After")
    wait_time = float(retry_after) if retry_after else backoff
    logger.warning("Rate limited (429), waiting %.1fs before retry %d/%d", wait_time, attempt + 1, _MAX_RETRIES)
    return wait_time


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
        self._api_key = api_key if api_key else _load_api_key_from_env_file()
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY not found in ~/.env")
        self._current_concurrency = _CONCURRENT_REQUESTS
        self._rate_limit_hits = 0
        logger.info("Initialized FieldExtractor with OpenAI API (model: %s)", _MODEL_NAME)

    async def extract_fields(self, condition_id: str, title: str, description: str, tokens: list[dict]) -> ExtractedFields | None:
        """Extract structured fields from a single Poly market."""
        outcomes = [t.get("outcome", "") for t in tokens]
        market_text = f"Title: {title}\nDescription: {description}\nOutcomes: {outcomes}"

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {
            "model": _MODEL_NAME,
            "messages": [
                {"role": "system", "content": _EXTRACTION_PROMPT_SINGLE},
                {"role": "user", "content": market_text},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        timeout = aiohttp.ClientTimeout(total=_API_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(_OPENAI_API_URL, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                result = await resp.json()

        response_text = result["choices"][0]["message"]["content"]
        return _parse_llm_response(response_text, condition_id)

    async def extract_and_store(
        self, condition_id: str, title: str, description: str, tokens: list[dict], redis: "Redis"
    ) -> ExtractedFields | None:
        """Extract fields and store in Redis if not already present."""
        redis_key = _get_redis_key(condition_id)

        existing = await redis.hgetall(redis_key)
        if existing:
            logger.debug("Using cached extracted fields for %s", condition_id)
            return ExtractedFields(
                condition_id=condition_id,
                category=existing.get(b"category", b"").decode(),
                underlying=existing.get(b"underlying", b"").decode(),
                floor_strike=float(existing[b"floor_strike"].decode()) if existing.get(b"floor_strike") else None,
                cap_strike=float(existing[b"cap_strike"].decode()) if existing.get(b"cap_strike") else None,
            )

        fields = await self.extract_fields(condition_id, title, description, tokens)
        if fields is None:
            return None

        field_map: dict[str, str] = {"category": fields.category, "underlying": fields.underlying}
        if fields.floor_strike is not None:
            field_map["floor_strike"] = str(fields.floor_strike)
        if fields.cap_strike is not None:
            field_map["cap_strike"] = str(fields.cap_strike)

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
            return self._parse_batch_response(response_text)
        except (RuntimeError, KeyError, json.JSONDecodeError):
            logger.exception("Batch API call failed")
            raise

    def _parse_batch_response(self, response_text: str) -> dict[str, ExtractedFields]:
        """Parse batch LLM response into ExtractedFields dict."""
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        data = json.loads(text)
        markets_data = data.get("markets", [])

        results: dict[str, ExtractedFields] = {}
        for item in markets_data:
            condition_id = item.get("id", "")
            if not condition_id:
                continue

            category = item.get("category", "Entertainment")
            if category not in KALSHI_CATEGORIES:
                category = "Entertainment"

            underlying = item.get("underlying", "")
            if not isinstance(underlying, str) or not underlying:
                logger.warning("Invalid underlying for %s: %s", condition_id, underlying)
                continue

            floor_strike = _parse_strike_value(item.get("floor_strike"))
            cap_strike = _parse_strike_value(item.get("cap_strike"))

            results[condition_id] = ExtractedFields(
                condition_id=condition_id,
                category=category,
                underlying=underlying.upper(),
                floor_strike=floor_strike,
                cap_strike=cap_strike,
            )

        return results

    async def extract_batch(self, markets: Sequence[dict], redis: "Redis") -> list[ExtractedFields]:
        """Extract fields for multiple markets with batching and concurrency."""
        results: list[ExtractedFields] = []
        to_extract: list[dict] = []
        cached_count = 0

        for market in markets:
            condition_id = market.get("condition_id", "")
            redis_key = _get_redis_key(condition_id)
            existing = await redis.hgetall(redis_key)

            if existing:
                cached_count += 1
                fields = ExtractedFields(
                    condition_id=condition_id,
                    category=existing.get(b"category", b"").decode(),
                    underlying=existing.get(b"underlying", b"").decode(),
                    floor_strike=float(existing[b"floor_strike"].decode()) if existing.get(b"floor_strike") else None,
                    cap_strike=float(existing[b"cap_strike"].decode()) if existing.get(b"cap_strike") else None,
                )
                results.append(fields)
            else:
                to_extract.append(market)

        if cached_count > 0:
            logger.info("Cache hits: %d, need to extract: %d", cached_count, len(to_extract))

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

        extracted_count = 0
        pipe = redis.pipeline()
        for batch_result in batch_results:
            for condition_id, fields in batch_result.items():
                results.append(fields)
                extracted_count += 1

                field_map: dict[str, str] = {"category": fields.category, "underlying": fields.underlying}
                if fields.floor_strike is not None:
                    field_map["floor_strike"] = str(fields.floor_strike)
                if fields.cap_strike is not None:
                    field_map["cap_strike"] = str(fields.cap_strike)

                redis_key = _get_redis_key(condition_id)
                pipe.hset(redis_key, mapping=field_map)

        await pipe.execute()

        logger.info("Field extraction complete: %d cached, %d newly extracted, %d total", cached_count, extracted_count, len(results))
        return results


__all__ = ["ExtractedFields", "FieldExtractor", "KALSHI_CATEGORIES"]
