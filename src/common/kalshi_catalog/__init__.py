"""Kalshi market catalog discovery.

This module provides utilities for discovering mutually exclusive markets
from the Kalshi API with proper filtering and validation.

Usage:
    from common.kalshi_catalog import discover_mutually_exclusive_markets

    events = await discover_mutually_exclusive_markets(
        client,
        expiry_window_seconds=3600,
        min_markets_per_event=2,
    )
"""

from .discovery import (
    DiscoveryResult,
    discover_mutually_exclusive_markets,
    discover_with_skipped_stats,
)
from .fetcher import (
    fetch_all_markets,
    fetch_event_details,
    fetch_event_details_batch,
)
from .filtering import (
    SkippedMarketStats,
    filter_markets_for_window,
    filter_mutually_exclusive_events,
    group_markets_by_event,
    is_expiring_within_window,
)
from .skipped_stats_store import get_skipped_stats, store_skipped_stats
from .types import (
    CatalogDiscoveryError,
    DiscoveredEvent,
    DiscoveredMarket,
    SkippedMarketsInfo,
)

__all__ = [
    # Main entry points
    "DiscoveryResult",
    "discover_mutually_exclusive_markets",
    "discover_with_skipped_stats",
    # Types
    "CatalogDiscoveryError",
    "DiscoveredEvent",
    "DiscoveredMarket",
    "SkippedMarketStats",
    "SkippedMarketsInfo",
    # Fetching
    "fetch_all_markets",
    "fetch_event_details",
    "fetch_event_details_batch",
    # Filtering
    "filter_markets_for_window",
    "filter_mutually_exclusive_events",
    "group_markets_by_event",
    "is_expiring_within_window",
    # Skipped stats storage
    "get_skipped_stats",
    "store_skipped_stats",
]
