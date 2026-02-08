"""Kalshi market catalog discovery.

This module provides utilities for discovering markets from the Kalshi API
with proper filtering and validation.

Usage:
    from common.kalshi_catalog import discover_with_skipped_stats

    events, skipped = await discover_with_skipped_stats(
        client,
        expiry_window_seconds=3600,
        min_markets_per_event=2,
    )
"""

from .discovery import discover_with_skipped_stats
from .fetcher import fetch_all_markets
from .filtering import SkippedMarketStats
from .skipped_stats_store import store_skipped_stats
from .types import (
    CatalogDiscoveryError,
    DiscoveredEvent,
    DiscoveredMarket,
    SkippedMarketsInfo,
)

__all__ = [
    # Main entry point
    "discover_with_skipped_stats",
    # Types
    "CatalogDiscoveryError",
    "DiscoveredEvent",
    "DiscoveredMarket",
    "SkippedMarketStats",
    "SkippedMarketsInfo",
    # Fetching
    "fetch_all_markets",
    # Skipped stats storage
    "store_skipped_stats",
]
