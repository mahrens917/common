#!/usr/bin/env python3
"""Live matching of Kalshi and Polymarket markets from Redis.

Usage:
    python -m scripts.live_match_markets [--threshold 0.75]
    python -m scripts.live_match_markets --extract-fields  # Extract structured fields using LLM
    python -m scripts.live_match_markets --match-by-fields  # Match using extracted fields

Requires:
    - Redis running with Kalshi and Poly market data
    - NOVITA_API_KEY in ~/.env (for embeddings)
    - OPENAI_API_KEY in ~/.env (for field extraction)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import orjson

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from redis.asyncio import Redis

from common.market_matcher import (
    EmbeddingService,
    ExtractedFields,
    FieldExtractor,
    MarketMatcher,
    MatchCandidate,
    clear_old_embedding_cache,
)
from common.redis_protocol.kalshi_store import KalshiStore

# Add poly to path for PolyStore
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "poly" / "src"))
import importlib

_poly_store_module = importlib.import_module("poly.store.poly_store")
PolyStore = _poly_store_module.PolyStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

EXPIRY_WINDOW_HOURS = 24.0


def _parse_iso_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string to datetime."""
    if not dt_str:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _parse_float(value) -> float | None:
    """Parse a value to float, returning None if invalid."""
    if value is None or value == "" or value == "inf":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def kalshi_redis_to_candidate(market: dict) -> MatchCandidate:
    """Convert a Kalshi market dict from Redis to MatchCandidate."""
    ticker = market.get("market_ticker", market.get("ticker", ""))
    title = market.get("event_title", market.get("title", ""))
    subtitle = market.get("subtitle", "")
    close_time = market.get("close_time", "")

    expiry = _parse_iso_datetime(close_time)
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    return MatchCandidate(
        market_id=ticker,
        title=title,
        description=subtitle,
        expiry=expiry,
        floor_strike=_parse_float(market.get("floor_strike")),
        cap_strike=_parse_float(market.get("cap_strike")),
        source="kalshi",
    )


def poly_redis_to_candidate(market: dict) -> MatchCandidate:
    """Convert a Poly market dict from Redis to MatchCandidate."""
    condition_id = market.get("condition_id", "")
    title = market.get("title", "")
    description = market.get("description", "")
    end_date_str = market.get("end_date", "")

    expiry = _parse_iso_datetime(end_date_str)
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    # Try to extract strikes from tokens
    floor_strike = None
    cap_strike = None
    tokens_str = market.get("tokens", "")
    if tokens_str:
        try:
            tokens = orjson.loads(tokens_str)
            floor_strike, cap_strike = _extract_strikes_from_tokens(tokens)
        except (orjson.JSONDecodeError, TypeError):
            pass

    return MatchCandidate(
        market_id=condition_id,
        title=title,
        description=description,
        expiry=expiry,
        floor_strike=floor_strike,
        cap_strike=cap_strike,
        source="poly",
    )


def _extract_strikes_from_tokens(tokens: list[dict]) -> tuple[float | None, float | None]:
    """Extract strike prices from token outcomes."""
    import re

    floor_strike = None
    cap_strike = None

    patterns_above = [
        r"(?:above|over|greater than|>=?)\s*\$?([\d,]+\.?\d*)",
        r"\$?([\d,]+\.?\d*)\s*(?:or more|\+)",
    ]
    patterns_below = [
        r"(?:below|under|less than|<=?)\s*\$?([\d,]+\.?\d*)",
        r"\$?([\d,]+\.?\d*)\s*(?:or less|-)",
    ]

    for token in tokens:
        outcome = token.get("outcome", "")
        if not isinstance(outcome, str):
            continue

        for pattern in patterns_above:
            match = re.search(pattern, outcome, re.IGNORECASE)
            if match:
                try:
                    floor_strike = float(match.group(1).replace(",", ""))
                except ValueError:
                    continue

        for pattern in patterns_below:
            match = re.search(pattern, outcome, re.IGNORECASE)
            if match:
                try:
                    cap_strike = float(match.group(1).replace(",", ""))
                except ValueError:
                    continue

    return floor_strike, cap_strike


async def fetch_kalshi_from_redis(redis: Redis) -> list[dict]:
    """Fetch all Kalshi markets from Redis."""
    logger.info("Fetching Kalshi markets from Redis...")
    store = KalshiStore(redis=redis)
    markets = await store.get_all_markets()
    logger.info("Found %d Kalshi markets in Redis", len(markets))
    return markets


async def fetch_poly_from_redis(redis: Redis) -> list[dict]:
    """Fetch all Poly markets from Redis."""
    logger.info("Fetching Poly markets from Redis...")
    store = PolyStore(redis)
    markets = await store.get_markets_by_volume(0)  # 0 = all markets
    logger.info("Found %d Poly markets in Redis", len(markets))

    # Log sample tokens for debugging strike extraction
    samples_with_tokens = [m for m in markets[:50] if m.get("tokens")][:3]
    for m in samples_with_tokens:
        tokens_str = m.get("tokens", "")
        try:
            tokens = orjson.loads(tokens_str)
            outcomes = [t.get("outcome", "") for t in tokens]
            logger.info("Sample Poly tokens - title: %s, outcomes: %s", m.get("title", "")[:50], outcomes)
        except (orjson.JSONDecodeError, TypeError):
            pass

    return markets


async def run_matching(
    kalshi_markets: list[dict],
    poly_markets: list[dict],
    similarity_threshold: float,
    redis: Redis,
    no_strike_filter: bool = False,
):
    """Run embedding-based matching with Redis caching."""
    logger.info("Initializing embedding service (Novita API)...")
    embedding_service = EmbeddingService()

    matcher = MarketMatcher(
        embedding_service,
        similarity_threshold=similarity_threshold,
        expiry_window_hours=EXPIRY_WINDOW_HOURS,
    )

    kalshi_candidates = [kalshi_redis_to_candidate(m) for m in kalshi_markets]
    poly_candidates = [poly_redis_to_candidate(m) for m in poly_markets]

    logger.info(
        "Matching %d Kalshi markets against %d Poly markets...",
        len(kalshi_candidates),
        len(poly_candidates),
    )

    if not kalshi_candidates or not poly_candidates:
        return [], kalshi_candidates, poly_candidates

    # Use cached matching
    matches = await matcher.match_with_cache(
        kalshi_candidates, poly_candidates, redis, skip_strike_filter=no_strike_filter
    )
    return matches, kalshi_candidates, poly_candidates


def print_results(matches, kalshi_markets: list[dict], poly_markets: list[dict]):
    """Print match results."""
    kalshi_lookup = {m.get("market_ticker", m.get("ticker", "")): m for m in kalshi_markets}
    poly_lookup = {m.get("condition_id", ""): m for m in poly_markets}

    print("\n" + "=" * 80)
    print(f"TOP {len(matches)} MATCHES (exact strike + expiry ±24h)")
    print("=" * 80)

    for i, match in enumerate(matches, 1):
        kalshi_market = kalshi_lookup.get(match.kalshi_market_id, {})
        poly_market = poly_lookup.get(match.poly_market_id, {})

        print(f"\n--- Match {i} (combined similarity: {match.title_similarity:.2%}) ---")

        if kalshi_market:
            title = kalshi_market.get("event_title", kalshi_market.get("title", "N/A"))
            subtitle = kalshi_market.get("subtitle", "")
            print(f"KALSHI: {title}")
            print(f"  Ticker: {match.kalshi_market_id}")
            if subtitle:
                sub_preview = subtitle[:80] + "..." if len(subtitle) > 80 else subtitle
                print(f"  Description: {sub_preview}")
            print(f"  Strike: floor={kalshi_market.get('floor_strike')}, cap={kalshi_market.get('cap_strike')}")
            print(f"  Expiry: {kalshi_market.get('close_time')}")

        if poly_market:
            title = poly_market.get("title", "N/A")
            description = poly_market.get("description", "")
            print(f"POLY: {title}")
            print(f"  ID: {match.poly_market_id}")
            if description:
                desc_preview = description[:80] + "..." if len(description) > 80 else description
                print(f"  Description: {desc_preview}")
            print(f"  Expiry: {poly_market.get('end_date')}")

        print(f"Expiry delta: {match.expiry_delta_hours:.1f}h")


async def extract_poly_fields(poly_markets: list[dict], redis: Redis, limit: int | None = None) -> list[ExtractedFields]:
    """Extract structured fields from Poly markets using LLM.

    Args:
        poly_markets: List of Poly market dicts.
        redis: Redis connection.
        limit: Optional limit on number of markets to extract.

    Returns:
        List of extracted fields.
    """
    logger.info("Initializing field extractor (OpenAI API)...")
    extractor = FieldExtractor()

    markets_to_extract = poly_markets[:limit] if limit else poly_markets
    logger.info("Extracting fields for %d Poly markets...", len(markets_to_extract))

    return await extractor.extract_batch(markets_to_extract, redis)


def _strikes_overlap(
    k_floor: float | None,
    k_cap: float | None,
    p_floor: float | None,
    p_cap: float | None,
    tolerance: float = 1.0,
) -> bool:
    """Check if Kalshi and Poly strikes match within tolerance.

    Markets must have the same "shape" to match:
        - Both "above X" (floor only): floors must be within tolerance
        - Both "below X" (cap only): caps must be within tolerance
        - Both "between X and Y" (floor and cap): both must be within tolerance
        - Both binary (no strikes): match on category/underlying only

    Args:
        k_floor: Kalshi floor strike
        k_cap: Kalshi cap strike (may be inf)
        p_floor: Poly floor strike
        p_cap: Poly cap strike (None treated as inf when floor exists)
        tolerance: Absolute tolerance for strike comparison (default 1.0)
    """
    # Normalize inf/None caps for both sides
    if k_cap is not None and (k_cap == float("inf") or k_cap > 1e10):
        k_cap = None
    if p_cap is not None and (p_cap == float("inf") or p_cap > 1e10):
        p_cap = None

    # Determine market "shape" for each side
    k_has_floor = k_floor is not None
    k_has_cap = k_cap is not None
    p_has_floor = p_floor is not None
    p_has_cap = p_cap is not None

    # Both must have same shape (above, below, between, or binary)
    if (k_has_floor, k_has_cap) != (p_has_floor, p_has_cap):
        return False

    # If neither has strikes, it's a binary market - match on category/underlying
    if not k_has_floor and not k_has_cap:
        return True

    # Compare floor strikes if both have them
    if k_has_floor and p_has_floor:
        if abs(k_floor - p_floor) > tolerance:
            return False

    # Compare cap strikes if both have them
    if k_has_cap and p_has_cap:
        if abs(k_cap - p_cap) > tolerance:
            return False

    return True


def _get_kalshi_underlying(market: dict) -> str:
    """Extract underlying asset code from Kalshi market."""
    ticker = market.get("market_ticker", market.get("ticker", ""))
    # Parse ticker like KXETHD-26JAN2123-T3509.99
    # Extract ETH from KXETHD
    if ticker.startswith("KX"):
        parts = ticker.split("-")
        if parts:
            code = parts[0][2:]  # Remove KX prefix
            # Remove trailing D (daily) or other suffixes
            if code.endswith("D"):
                code = code[:-1]
            return code.upper()
    return ""


def match_by_category_and_strike(
    kalshi_markets: list[dict],
    poly_fields: list[ExtractedFields],
    poly_markets: list[dict],
) -> list[tuple[dict, ExtractedFields, dict]]:
    """Match markets based on category, underlying, and strike ranges.

    Args:
        kalshi_markets: List of Kalshi market dicts.
        poly_fields: List of extracted fields from Poly markets.
        poly_markets: List of Poly market dicts.

    Returns:
        List of (kalshi_market, poly_fields, poly_market) tuples.
    """
    matches: list[tuple[dict, ExtractedFields, dict]] = []
    poly_lookup = {m.get("condition_id", ""): m for m in poly_markets}

    # Group poly fields by (category, underlying) for faster lookup
    poly_by_key: dict[tuple[str, str], list[ExtractedFields]] = {}
    for fields in poly_fields:
        key = (fields.category.lower(), fields.underlying.upper())
        poly_by_key.setdefault(key, []).append(fields)

    logger.info(
        "Field-based matching: %d Kalshi markets vs %d Poly extracted fields",
        len(kalshi_markets),
        len(poly_fields),
    )
    logger.info("Poly (category, underlying) groups: %d unique", len(poly_by_key))

    for kalshi in kalshi_markets:
        kalshi_category = kalshi.get("category", "").lower()
        kalshi_underlying = _get_kalshi_underlying(kalshi)
        kalshi_floor = _parse_float(kalshi.get("floor_strike"))
        kalshi_cap = _parse_float(kalshi.get("cap_strike"))

        # Only check poly markets with same category AND underlying
        key = (kalshi_category, kalshi_underlying)
        matching_poly = poly_by_key.get(key, [])

        for fields in matching_poly:
            # Normalize Poly cap: None means inf for "above X" markets
            p_cap = fields.cap_strike
            if p_cap is None and fields.floor_strike is not None:
                p_cap = float("inf")

            # Check strike ranges overlap
            if not _strikes_overlap(kalshi_floor, kalshi_cap, fields.floor_strike, p_cap):
                continue

            poly_market = poly_lookup.get(fields.condition_id, {})
            matches.append((kalshi, fields, poly_market))

    logger.info("Found %d field-based matches", len(matches))
    return matches


def print_field_extraction_results(fields: list[ExtractedFields]) -> None:
    """Print field extraction summary."""
    print("\n" + "=" * 80)
    print(f"EXTRACTED FIELDS FOR {len(fields)} POLY MARKETS")
    print("=" * 80)

    # Category distribution
    categories: dict[str, int] = {}
    for f in fields:
        categories[f.category] = categories.get(f.category, 0) + 1

    print("\nCategory distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Underlying distribution (top 20)
    underlyings: dict[str, int] = {}
    for f in fields:
        underlyings[f.underlying] = underlyings.get(f.underlying, 0) + 1

    print("\nTop underlyings:")
    for underlying, count in sorted(underlyings.items(), key=lambda x: -x[1])[:20]:
        print(f"  {underlying}: {count}")

    # Sample extractions
    print("\nSample extractions:")
    for f in fields[:10]:
        floor_str = f"floor={f.floor_strike}" if f.floor_strike is not None else ""
        cap_str = f"cap={f.cap_strike}" if f.cap_strike is not None else ""
        strike_str = ", ".join(filter(None, [floor_str, cap_str])) if floor_str or cap_str else "no strikes"
        print(f"  [{f.category}] {f.underlying} ({strike_str})")


def print_field_match_results(
    matches: list[tuple[dict, ExtractedFields, dict]],
) -> None:
    """Print field-based match results."""
    print("\n" + "=" * 80)
    print(f"FIELD-BASED MATCHES: {len(matches)}")
    print("=" * 80)

    for i, (kalshi, fields, poly) in enumerate(matches[:20], 1):
        kalshi_title = kalshi.get("event_title", kalshi.get("title", "N/A"))
        poly_title = poly.get("title", "N/A")

        print(f"\n--- Match {i} ---")
        print(f"Category: {fields.category} | Underlying: {fields.underlying}")
        print(f"KALSHI: {kalshi_title}")
        print(f"  Ticker: {kalshi.get('market_ticker', kalshi.get('ticker', ''))}")
        print(f"  Strike: floor={kalshi.get('floor_strike')}, cap={kalshi.get('cap_strike')}")
        print(f"POLY: {poly_title}")
        print(f"  Underlying: {fields.underlying}")
        print(f"  Strike: floor={fields.floor_strike}, cap={fields.cap_strike}")


async def main(
    threshold: float,
    redis_url: str,
    no_strike_filter: bool = False,
    extract_fields: bool = False,
    match_by_fields: bool = False,
    extract_limit: int | None = None,
):
    """Main entry point."""
    redis = Redis.from_url(redis_url)

    try:
        # Clear old 0.6B model embeddings if any exist
        await clear_old_embedding_cache(redis)

        kalshi_markets = await fetch_kalshi_from_redis(redis)
        poly_markets = await fetch_poly_from_redis(redis)

        if not kalshi_markets:
            logger.warning("No Kalshi markets found in Redis")
            return

        if not poly_markets:
            logger.warning("No Poly markets found in Redis")
            return

        # Field extraction mode
        if extract_fields:
            fields = await extract_poly_fields(poly_markets, redis, extract_limit)
            print_field_extraction_results(fields)
            return

        # Field-based matching mode
        if match_by_fields:
            extractor = FieldExtractor()
            fields = await extractor.extract_batch(poly_markets, redis)
            matches = match_by_category_and_strike(kalshi_markets, fields, poly_markets)
            print_field_match_results(matches)
            return

        # Embedding-based matching (original behavior)
        matches, _, _ = await run_matching(kalshi_markets, poly_markets, threshold, redis, no_strike_filter)
        print_results(matches, kalshi_markets, poly_markets)

    finally:
        await redis.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match Kalshi and Polymarket markets from Redis")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Minimum similarity threshold (default: 0.75)",
    )
    parser.add_argument(
        "--redis-url",
        type=str,
        default="redis://localhost:6379",
        help="Redis URL (default: redis://localhost:6379)",
    )
    parser.add_argument(
        "--no-strike-filter",
        action="store_true",
        help="Disable strike matching filter (match by embedding similarity only)",
    )
    parser.add_argument(
        "--extract-fields",
        action="store_true",
        help="Extract structured fields from Poly markets using LLM (stores in Redis)",
    )
    parser.add_argument(
        "--match-by-fields",
        action="store_true",
        help="Match markets using extracted fields instead of embeddings",
    )
    parser.add_argument(
        "--extract-limit",
        type=int,
        help="Limit number of markets to extract (for testing)",
    )
    args = parser.parse_args()

    asyncio.run(
        main(
            args.threshold,
            args.redis_url,
            args.no_strike_filter,
            args.extract_fields,
            args.match_by_fields,
            args.extract_limit,
        )
    )
