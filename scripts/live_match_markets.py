#!/usr/bin/env python3
"""Live matching of Kalshi and Polymarket markets from Redis.

Usage:
    python -m scripts.live_match_markets [--threshold 0.75]

Requires:
    - Redis running with Kalshi and Poly market data
    - pip install torch transformers
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

from common.market_matcher import EmbeddingService, MarketMatcher, MatchCandidate
from common.redis_protocol.kalshi_store import KalshiStore

# Add poly to path for PolyStore
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "poly" / "src"))
from poly.store.poly_store import PolyStore

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
    return markets


async def run_matching(
    kalshi_markets: list[dict],
    poly_markets: list[dict],
    similarity_threshold: float,
    redis: Redis,
):
    """Run embedding-based matching with Redis caching."""
    logger.info("Initializing Qwen embedding model...")
    embedding_service = EmbeddingService(device="cpu")
    logger.info("Using device: %s", embedding_service.device)

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

    # Use cached matching with strike filter
    matches = await matcher.match_with_cache_and_strike_filter(
        kalshi_candidates, poly_candidates, redis
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


async def main(threshold: float, redis_url: str):
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

        matches, _, _ = await run_matching(kalshi_markets, poly_markets, threshold, redis)
        print_results(matches, kalshi_markets, poly_markets)

    finally:
        await redis.close()


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
    args = parser.parse_args()

    asyncio.run(main(args.threshold, args.redis_url))
