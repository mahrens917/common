#!/usr/bin/env python3
"""Match Kalshi and Polymarket markets using embedding similarity.

Usage:
    python -m scripts.match_markets

Requires:
    NOVITA_API_KEY in ~/.env
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.kalshi_catalog.discovery import discover_all_markets
from common.market_matcher import (
    EmbeddingService,
    MarketMatcher,
    kalshi_market_to_candidate,
    poly_market_to_candidate,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

EXPIRY_WINDOW_SECONDS = 24 * 3600  # 24 hours


async def fetch_kalshi_markets(client):
    """Fetch Kalshi markets within expiry window."""
    events = await discover_all_markets(
        client,
        expiry_window_seconds=EXPIRY_WINDOW_SECONDS,
        min_markets_per_event=1,
    )
    logger.info("Fetched %d Kalshi events", len(events))
    return events


async def fetch_poly_markets(service):
    """Fetch Polymarket markets."""
    await service.fetch_and_store_markets()
    markets = service.get_markets()
    logger.info("Fetched %d Poly markets", len(markets))
    return markets


async def run_matching(kalshi_events, poly_markets, similarity_threshold: float = 0.75):
    """Run the matching algorithm."""
    logger.info("Initializing embedding service (Novita API)...")
    embedding_service = EmbeddingService()

    matcher = MarketMatcher(
        embedding_service,
        similarity_threshold=similarity_threshold,
        expiry_window_hours=24.0,
    )

    kalshi_candidates = [
        kalshi_market_to_candidate(market, event.title)
        for event in kalshi_events
        for market in event.markets
    ]
    poly_candidates = [poly_market_to_candidate(m) for m in poly_markets]

    logger.info(
        "Matching %d Kalshi markets against %d Poly markets...",
        len(kalshi_candidates),
        len(poly_candidates),
    )

    matches = await matcher.match_with_strike_filter(kalshi_candidates, poly_candidates)
    return matches


def print_matches(matches, kalshi_events, poly_markets):
    """Print match results."""
    kalshi_lookup = {
        market.ticker: (event, market)
        for event in kalshi_events
        for market in event.markets
    }
    poly_lookup = {m.condition_id: m for m in poly_markets}

    print("\n" + "=" * 80)
    print(f"FOUND {len(matches)} MATCHES")
    print("=" * 80)

    for i, match in enumerate(matches, 1):
        kalshi_event, kalshi_market = kalshi_lookup.get(match.kalshi_market_id, (None, None))
        poly_market = poly_lookup.get(match.poly_market_id)

        print(f"\n--- Match {i} (similarity: {match.title_similarity:.2%}) ---")
        print(f"Kalshi: {kalshi_event.title if kalshi_event else 'N/A'}")
        print(f"  Market: {match.kalshi_market_id}")
        if kalshi_market:
            print(f"  Strike: floor={kalshi_market.floor_strike}, cap={kalshi_market.cap_strike}")
        print(f"Poly: {poly_market.title if poly_market else 'N/A'}")
        print(f"  Market: {match.poly_market_id}")
        print(f"Expiry delta: {match.expiry_delta_hours:.1f} hours")
        print(f"Strike match: {match.strike_match}")


async def main_async(kalshi_client, poly_service, similarity_threshold: float):
    """Main async entry point."""
    kalshi_events = await fetch_kalshi_markets(kalshi_client)
    poly_markets = await fetch_poly_markets(poly_service)

    if not kalshi_events:
        logger.warning("No Kalshi events found within expiry window")
        return

    if not poly_markets:
        logger.warning("No Poly markets found")
        return

    matches = await run_matching(kalshi_events, poly_markets, similarity_threshold)
    print_matches(matches, kalshi_events, poly_markets)


def main():
    """Entry point - set up clients and run."""
    parser = argparse.ArgumentParser(description="Match Kalshi and Polymarket markets")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Minimum similarity threshold (default: 0.75)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be matched without fetching live data",
    )
    args = parser.parse_args()

    if args.dry_run:
        logger.info("Dry run mode - showing embedding service initialization only")
        embedding_service = EmbeddingService()
        logger.info("Using Novita API")

        async def test_embeddings():
            test_texts = ["Bitcoin price above 100k", "BTC will exceed $100,000"]
            embeddings = await embedding_service.embed(test_texts)
            similarity = embedding_service.compute_similarity_matrix(embeddings, embeddings)
            logger.info("Test similarity between sample texts: %.2f", similarity[0, 1])

        asyncio.run(test_embeddings())
        return

    # For actual usage, you need to set up clients:
    print("To run with live data, you need to set up the clients:")
    print()
    print("```python")
    print("from kalshi.client import KalshiClient")
    print("from poly.service import PolymarketService")
    print()
    print("kalshi_client = KalshiClient(...)")
    print("poly_service = PolymarketService()")
    print("await poly_service.initialize()")
    print()
    print("await main_async(kalshi_client, poly_service, threshold)")
    print("```")
    print()
    print("Or run with --dry-run to test the embedding model.")


if __name__ == "__main__":
    main()
