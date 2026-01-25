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

from common.llm_extractor import MarketExtraction, MarketExtractor
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


def _poly_market_to_extractor_input(market: dict) -> dict:
    """Convert a Poly market dict from Redis into the format expected by MarketExtractor."""
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


async def extract_poly_fields(
    poly_markets: list[dict], redis: Redis, limit: int | None = None
) -> list[MarketExtraction]:
    """Extract structured fields from Poly markets using Claude Opus.

    Args:
        poly_markets: List of Poly market dicts from Redis.
        redis: Redis connection.
        limit: Optional limit on number of markets to extract.

    Returns:
        List of MarketExtraction results.
    """
    logger.info("Initializing field extractor (Claude Opus)...")
    extractor = MarketExtractor(platform="poly")

    markets_to_extract = poly_markets[:limit] if limit else poly_markets
    extractor_inputs = [_poly_market_to_extractor_input(m) for m in markets_to_extract]
    logger.info("Extracting fields for %d Poly markets...", len(extractor_inputs))

    return await extractor.extract_batch(extractor_inputs, redis)


def _strikes_overlap(
    k_floor: float | None,
    k_cap: float | None,
    p_floor: float | None,
    p_cap: float | None,
    tolerance: float = 0.001,
) -> bool:
    """Check if Kalshi and Poly strikes match within tolerance.

    Markets must have the same "shape" to match:
        - Both "above X" (floor only): floors must be within tolerance
        - Both "below X" (cap only): caps must be within tolerance
        - Both "between X and Y" (floor and cap): both must be within tolerance
        - Both binary (no strikes): match on category/underlying only
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
        ref = max(abs(k_floor), abs(p_floor), 1.0)
        if abs(k_floor - p_floor) / ref > tolerance:
            return False

    # Compare cap strikes if both have them
    if k_has_cap and p_has_cap:
        ref = max(abs(k_cap), abs(p_cap), 1.0)
        if abs(k_cap - p_cap) / ref > tolerance:
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


def _get_kalshi_subject(market: dict) -> str:
    """Extract subject code from Kalshi ticker.

    For tickers like KXRT-MER-35, the subject is MER (specific movie).
    For crypto tickers like KXETHD-26JAN2123-T3509.99, the second segment
    is a date, so the subject defaults to the underlying.
    """
    ticker = market.get("market_ticker", market.get("ticker", ""))
    if not ticker.startswith("KX"):
        return _get_kalshi_underlying(market)
    parts = ticker.split("-")
    if len(parts) < 2:
        return _get_kalshi_underlying(market)
    second = parts[1]
    # Date segments contain digits mixed with month abbreviations (e.g., 26JAN2123)
    # or start with T followed by digits (strike values like T3509.99)
    has_digit = any(c.isdigit() for c in second)
    if has_digit:
        return _get_kalshi_underlying(market)
    return second.upper()


def match_by_category_and_strike(
    kalshi_markets: list[dict],
    poly_fields: list[MarketExtraction],
    poly_markets: list[dict],
) -> tuple[list[tuple[dict, MarketExtraction, dict]], list[dict]]:
    """Match markets based on category, underlying, subject, and strike ranges.

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

    # Group poly fields by (category, underlying, subject) for faster lookup
    poly_by_key: dict[tuple[str, str, str], list[MarketExtraction]] = {}
    for fields in poly_fields:
        key = (fields.category.lower(), fields.underlying.upper(), fields.subject.upper())
        poly_by_key.setdefault(key, []).append(fields)

    logger.info(
        "Field-based matching: %d Kalshi markets vs %d Poly extracted fields",
        len(kalshi_markets),
        len(poly_fields),
    )
    logger.info("Poly (category, underlying, subject) groups: %d unique", len(poly_by_key))

    for kalshi in kalshi_markets:
        _match_single_kalshi(kalshi, poly_by_key, poly_lookup, matches, near_misses)

    logger.info("Found %d field-based matches, %d near-misses", len(matches), len(near_misses))
    return matches, near_misses


def _match_single_kalshi(
    kalshi: dict,
    poly_by_key: dict[tuple[str, str, str], list[MarketExtraction]],
    poly_lookup: dict[str, dict],
    matches: list[tuple[dict, MarketExtraction, dict]],
    near_misses: list[dict],
) -> None:
    """Match a single Kalshi market against all poly groups."""
    kalshi_category = kalshi.get("category", "").lower()
    kalshi_underlying = _get_kalshi_underlying(kalshi)
    kalshi_subject = _get_kalshi_subject(kalshi)
    kalshi_floor = _parse_float(kalshi.get("floor_strike"))
    kalshi_cap = _parse_float(kalshi.get("cap_strike"))
    kalshi_expiry = _parse_iso_datetime(kalshi.get("close_time", ""))
    if kalshi_expiry.tzinfo is None:
        kalshi_expiry = kalshi_expiry.replace(tzinfo=timezone.utc)

    key = (kalshi_category, kalshi_underlying, kalshi_subject)
    matching_poly = poly_by_key.get(key, [])

    for fields in matching_poly:
        poly_market = poly_lookup.get(fields.market_id, {})
        _evaluate_match(kalshi, fields, poly_market, kalshi_floor, kalshi_cap, kalshi_expiry, matches, near_misses)


def _evaluate_match(
    kalshi: dict,
    fields: MarketExtraction,
    poly_market: dict,
    kalshi_floor: float | None,
    kalshi_cap: float | None,
    kalshi_expiry: datetime,
    matches: list[tuple[dict, MarketExtraction, dict]],
    near_misses: list[dict],
) -> None:
    """Evaluate a single Kalshi-Poly pair for matching."""
    poly_expiry = _parse_iso_datetime(poly_market.get("end_date", ""))
    if poly_expiry.tzinfo is None:
        poly_expiry = poly_expiry.replace(tzinfo=timezone.utc)
    expiry_delta_min = abs((kalshi_expiry - poly_expiry).total_seconds()) / 60.0

    # Normalize Poly cap: None means inf for "above X" markets
    p_cap = fields.cap_strike
    if p_cap is None and fields.floor_strike is not None:
        p_cap = float("inf")

    floor_pct = _strike_pct_delta(kalshi_floor, fields.floor_strike)
    cap_pct = _strike_pct_delta(kalshi_cap, p_cap)

    rejected_expiry = expiry_delta_min > EXPIRY_WINDOW_MINUTES
    rejected_strike = not _strikes_overlap(kalshi_floor, kalshi_cap, fields.floor_strike, p_cap)

    if not rejected_expiry and not rejected_strike:
        matches.append((kalshi, fields, poly_market))
    elif not rejected_expiry and rejected_strike:
        near_misses.append({"kalshi": kalshi, "fields": fields, "poly": poly_market,
                            "expiry_delta_min": expiry_delta_min, "floor_pct": floor_pct, "cap_pct": cap_pct})
    elif rejected_expiry and not rejected_strike and expiry_delta_min <= 1440.0:
        near_misses.append({"kalshi": kalshi, "fields": fields, "poly": poly_market,
                            "expiry_delta_min": expiry_delta_min, "floor_pct": floor_pct, "cap_pct": cap_pct})


def _strike_pct_delta(a: float | None, b: float | None) -> float | None:
    """Compute percentage delta between two strike values."""
    if a is None or b is None:
        return None
    if (a == float("inf") or a > 1e10) and (b == float("inf") or b > 1e10):
        return 0.0
    if a == float("inf") or a > 1e10 or b == float("inf") or b > 1e10:
        return None
    ref = max(abs(a), abs(b), 1.0)
    return abs(a - b) / ref


def print_field_extraction_results(fields: list[MarketExtraction]) -> None:
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
    matches: list[tuple[dict, MarketExtraction, dict]],
) -> None:
    """Print field-based match results."""
    print("\n" + "=" * 80)
    print(f"FIELD-BASED MATCHES: {len(matches)}")
    print("=" * 80)

    for i, (kalshi, fields, poly) in enumerate(matches, 1):
        kalshi_title = kalshi.get("event_title", kalshi.get("title", "N/A"))
        poly_title = poly.get("title", "N/A")

        print(f"\n--- Match {i} ---")
        print(f"Category: {fields.category} | Underlying: {fields.underlying} | Subject: {fields.subject}")
        print(f"KALSHI: {kalshi_title}")
        print(f"  Ticker: {kalshi.get('market_ticker', kalshi.get('ticker', ''))}")
        print(f"  Strike: floor={kalshi.get('floor_strike')}, cap={kalshi.get('cap_strike')}")
        print(f"  Expiry: {kalshi.get('close_time')}")
        print(f"POLY: {poly_title}")
        print(f"  Underlying: {fields.underlying}")
        print(f"  Strike: floor={fields.floor_strike}, cap={fields.cap_strike}")
        print(f"  Expiry: {poly.get('end_date')}")


def print_near_misses(near_misses: list[dict]) -> None:
    """Print near-miss diagnostics sorted by closest to matching."""
    if not near_misses:
        return

    def sort_key(nm: dict) -> float:
        expiry_score = nm["expiry_delta_min"] / 60.0
        floor_score = (nm["floor_pct"] or 0.0) * 100
        cap_score = (nm["cap_pct"] or 0.0) * 100
        return expiry_score + floor_score + cap_score

    sorted_misses = sorted(near_misses, key=sort_key)

    print("\n" + "=" * 80)
    print(f"NEAR MISSES (matched category+underlying, failed expiry/strike): {len(sorted_misses)}")
    print("=" * 80)

    for i, nm in enumerate(sorted_misses, 1):
        kalshi = nm["kalshi"]
        fields = nm["fields"]
        poly = nm["poly"]

        kalshi_title = kalshi.get("event_title", kalshi.get("title", "N/A"))

        parts = [f"expiry delta={nm['expiry_delta_min']:.1f}min"]
        if nm["floor_pct"] is not None:
            parts.append(f"floor delta={nm['floor_pct'] * 100:.2f}%")
        if nm["cap_pct"] is not None:
            parts.append(f"cap delta={nm['cap_pct'] * 100:.2f}%")

        print(f"\n--- Near Miss {i} ---")
        print(f"Category: {fields.category} | Underlying: {fields.underlying} | Subject: {fields.subject}")
        print(f"Deltas: {' | '.join(parts)}")
        print(f"KALSHI: {kalshi_title}")
        print(f"  Ticker: {kalshi.get('market_ticker', kalshi.get('ticker', ''))}")
        print(f"  Strike: floor={kalshi.get('floor_strike')}, cap={kalshi.get('cap_strike')}")
        print(f"  Expiry: {kalshi.get('close_time')}")
        print(f"POLY: {poly.get('title', 'N/A')}")
        print(f"  Underlying: {fields.underlying}")
        print(f"  Strike: floor={fields.floor_strike}, cap={fields.cap_strike}")
        print(f"  Expiry: {poly.get('end_date')}")


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
        extractor = MarketExtractor(platform="poly")
        extractor_inputs = [_poly_market_to_extractor_input(m) for m in poly_markets]
        fields = await extractor.extract_batch(extractor_inputs, redis)
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
    parser.add_argument(
        "--redis-url",
        type=str,
        default="redis://localhost:6379",
        help="Redis URL (default: redis://localhost:6379)",
    )
    parser.add_argument(
        "--extract-fields",
        action="store_true",
        help="Extract structured fields from Poly markets using LLM (stores in Redis)",
    )
    parser.add_argument(
        "--exclude-crypto",
        action="store_true",
        help="Exclude crypto markets from matching",
    )
    parser.add_argument(
        "--extract-limit",
        type=int,
        help="Limit number of markets to extract (for testing)",
    )
    args = parser.parse_args()

    asyncio.run(
        main(
            args.redis_url,
            args.extract_fields,
            args.extract_limit,
            args.exclude_crypto,
        )
    )
