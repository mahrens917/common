#!/usr/bin/env python3
"""Live matching of Kalshi and Polymarket markets from Redis.

Usage:
    python -m scripts.live_match_markets                        # Match using extracted fields (default)
    python -m scripts.live_match_markets --extract-fields       # Extract structured fields using LLM
    python -m scripts.live_match_markets --exclude-crypto       # Exclude crypto markets

Requires:
    - Redis running with Kalshi and Poly market data
    - ANTHROPIC_API_KEY in ~/.env (for field extraction via Claude Opus)
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
from scripts.match_display import print_field_extraction_results, print_field_match_results, print_near_misses

from common.llm_extractor import MarketExtraction, PolyExtractor
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

EXPIRY_WINDOW_MINUTES = 1.0
NEAR_MISS_EXPIRY_LIMIT_MINUTES = 1440.0
CAP_INFINITY_THRESHOLD = 1e10
_NON_FLOAT_VALUES = {"", "inf"}


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
    if value is None or value in _NON_FLOAT_VALUES:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _poly_market_to_extractor_input(market: dict) -> dict:
    """Convert a Poly market dict from Redis into the format expected by PolyExtractor."""
    condition_id = market.get("condition_id", "")
    title = market.get("title", "")
    result: dict = {"id": condition_id, "title": title}

    description = market.get("description")
    if description:
        result["description"] = description

    tokens_str = market.get("tokens")
    if tokens_str:
        try:
            tokens = orjson.loads(tokens_str)
            outcomes = [t.get("outcome", "") for t in tokens]
            result["tokens"] = str(outcomes)
        except (orjson.JSONDecodeError, TypeError):
            pass

    return result


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
    return markets


async def extract_poly_fields(poly_markets: list[dict], redis: Redis, limit: int | None = None) -> list[MarketExtraction]:
    """Extract structured fields from Poly markets using Claude Opus.

    Args:
        poly_markets: List of Poly market dicts from Redis.
        redis: Redis connection.
        limit: Optional limit on number of markets to extract.

    Returns:
        List of MarketExtraction results.
    """
    logger.info("Initializing field extractor...")
    extractor = PolyExtractor()

    markets_to_extract = poly_markets[:limit] if limit else poly_markets
    extractor_inputs = [_poly_market_to_extractor_input(m) for m in markets_to_extract]
    logger.info("Extracting fields for %d Poly markets...", len(extractor_inputs))

    return await extractor.extract_batch(extractor_inputs, set(), set(), redis)


def _is_effectively_infinite(value: float | None) -> bool:
    """Check if a cap value represents infinity."""
    return value is not None and (value == float("inf") or value > CAP_INFINITY_THRESHOLD)


def _normalize_cap(cap: float | None) -> float | None:
    """Normalize infinite/huge caps to None."""
    return None if _is_effectively_infinite(cap) else cap


def _values_within_tolerance(a: float, b: float, tolerance: float) -> bool:
    """Check if two values are within relative tolerance."""
    ref = max(abs(a), abs(b), 1.0)
    return abs(a - b) / ref <= tolerance


def _strikes_overlap(
    k_floor: float | None,
    k_cap: float | None,
    p_floor: float | None,
    p_cap: float | None,
    tolerance: float = 0.001,
) -> bool:
    """Check if Kalshi and Poly strikes match within tolerance."""
    k_cap = _normalize_cap(k_cap)
    p_cap = _normalize_cap(p_cap)

    k_shape = (k_floor is not None, k_cap is not None)
    p_shape = (p_floor is not None, p_cap is not None)

    if k_shape != p_shape:
        return False
    if k_shape == (False, False):
        return True
    if k_floor is not None and p_floor is not None:
        if not _values_within_tolerance(k_floor, p_floor, tolerance):
            return False
    if k_cap is not None and p_cap is not None:
        if not _values_within_tolerance(k_cap, p_cap, tolerance):
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
    poly_fields: list[MarketExtraction],
    poly_markets: list[dict],
) -> tuple[list[tuple[dict, MarketExtraction, dict]], list[dict]]:
    """Match markets based on category, underlying, and strike ranges.

    Args:
        kalshi_markets: List of Kalshi market dicts.
        poly_fields: List of MarketExtraction results from Poly markets.
        poly_markets: List of Poly market dicts.

    Returns:
        Tuple of (matches, near_misses).
    """
    matches: list[tuple[dict, MarketExtraction, dict]] = []
    near_misses: list[dict] = []
    poly_lookup = {m.get("condition_id", ""): m for m in poly_markets}

    # Group poly fields by (category, underlying) for faster lookup
    poly_by_key: dict[tuple[str, str], list[MarketExtraction]] = {}
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
        _match_single_kalshi(kalshi, poly_by_key, poly_lookup, matches, near_misses)

    logger.info("Found %d field-based matches, %d near-misses", len(matches), len(near_misses))
    return matches, near_misses


def _match_single_kalshi(
    kalshi: dict,
    poly_by_key: dict[tuple[str, str], list[MarketExtraction]],
    poly_lookup: dict[str, dict],
    matches: list[tuple[dict, MarketExtraction, dict]],
    near_misses: list[dict],
) -> None:
    """Match a single Kalshi market against all poly groups."""
    kalshi_category = kalshi.get("category", "").lower()
    kalshi_underlying = _get_kalshi_underlying(kalshi)
    kalshi_floor = _parse_float(kalshi.get("floor_strike"))
    kalshi_cap = _parse_float(kalshi.get("cap_strike"))
    kalshi_expiry = _parse_iso_datetime(kalshi.get("close_time", ""))
    if kalshi_expiry.tzinfo is None:
        kalshi_expiry = kalshi_expiry.replace(tzinfo=timezone.utc)

    key = (kalshi_category, kalshi_underlying)
    kalshi_strikes = (kalshi_floor, kalshi_cap)
    for fields in poly_by_key.get(key, []):
        poly_market = poly_lookup.get(fields.market_id, {})
        _classify_match(kalshi, fields, poly_market, kalshi_strikes, kalshi_expiry, matches, near_misses)


def _compute_expiry_delta_min(kalshi_expiry: datetime, poly_market: dict) -> float:
    """Compute absolute expiry difference in minutes between two markets."""
    poly_expiry = _parse_iso_datetime(poly_market.get("end_date", ""))
    if poly_expiry.tzinfo is None:
        poly_expiry = poly_expiry.replace(tzinfo=timezone.utc)
    return abs((kalshi_expiry - poly_expiry).total_seconds()) / 60.0


def _effective_poly_cap(fields: MarketExtraction) -> float | None:
    """Get effective poly cap, treating floor-only markets as inf cap."""
    if fields.cap_strike is None and fields.floor_strike is not None:
        return float("inf")
    return fields.cap_strike


def _classify_match(kalshi, fields, poly_market, kalshi_strikes, kalshi_expiry, matches, near_misses) -> None:
    """Classify a Kalshi-Poly pair as match, near-miss, or skip."""
    kalshi_floor, kalshi_cap = kalshi_strikes
    expiry_delta_min = _compute_expiry_delta_min(kalshi_expiry, poly_market)
    p_cap = _effective_poly_cap(fields)

    rejected_expiry = expiry_delta_min > EXPIRY_WINDOW_MINUTES
    rejected_strike = not _strikes_overlap(kalshi_floor, kalshi_cap, fields.floor_strike, p_cap)

    if not rejected_expiry and not rejected_strike:
        matches.append((kalshi, fields, poly_market))
        return

    is_near_miss = (not rejected_expiry and rejected_strike) or (
        rejected_expiry and not rejected_strike and expiry_delta_min <= NEAR_MISS_EXPIRY_LIMIT_MINUTES
    )
    if is_near_miss:
        floor_pct = _strike_pct_delta(kalshi_floor, fields.floor_strike)
        cap_pct = _strike_pct_delta(kalshi_cap, p_cap)
        near_misses.append(
            {
                "kalshi": kalshi,
                "fields": fields,
                "poly": poly_market,
                "expiry_delta_min": expiry_delta_min,
                "floor_pct": floor_pct,
                "cap_pct": cap_pct,
            }
        )


def _strike_pct_delta(a: float | None, b: float | None) -> float | None:
    """Compute percentage delta between two strike values."""
    if a is None or b is None:
        return None
    a_inf = _is_effectively_infinite(a)
    b_inf = _is_effectively_infinite(b)
    if a_inf and b_inf:
        return 0.0
    if a_inf or b_inf:
        return None
    ref = max(abs(a), abs(b), 1.0)
    return abs(a - b) / ref


async def main(
    redis_url: str,
    extract_fields: bool = False,
    extract_limit: int | None = None,
    exclude_crypto: bool = False,
):
    """Main entry point."""
    redis = Redis.from_url(redis_url)

    try:
        kalshi_markets = await fetch_kalshi_from_redis(redis)
        poly_markets = await fetch_poly_from_redis(redis)

        if not kalshi_markets:
            logger.warning("No Kalshi markets found in Redis")
            return

        if not poly_markets:
            logger.warning("No Poly markets found in Redis")
            return

        # Field extraction only mode
        if extract_fields:
            fields = await extract_poly_fields(poly_markets, redis, extract_limit)
            print_field_extraction_results(fields)
            return

        # Field-based matching (default mode)
        extractor = PolyExtractor()
        extractor_inputs = [_poly_market_to_extractor_input(m) for m in poly_markets]
        fields = await extractor.extract_batch(extractor_inputs, set(), set(), redis)
        if exclude_crypto:
            kalshi_markets = [m for m in kalshi_markets if m.get("category", "").lower() != "crypto"]
            fields = [f for f in fields if f.category.lower() != "crypto"]
            logger.info("Excluded crypto: %d Kalshi, %d Poly fields remain", len(kalshi_markets), len(fields))
        matches, near_misses = match_by_category_and_strike(kalshi_markets, fields, poly_markets)
        print_field_match_results(matches)
        print_near_misses(near_misses)

    finally:
        await redis.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match Kalshi and Polymarket markets from Redis")
    parser.add_argument("--redis-url", type=str, default="redis://localhost:6379", help="Redis URL")
    parser.add_argument("--extract-fields", action="store_true", help="Extract structured fields using LLM")
    parser.add_argument("--exclude-crypto", action="store_true", help="Exclude crypto markets from matching")
    parser.add_argument("--extract-limit", type=int, help="Limit number of markets to extract")
    args = parser.parse_args()
    asyncio.run(main(args.redis_url, args.extract_fields, args.extract_limit, args.exclude_crypto))
