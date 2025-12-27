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

from .discovery import discover_mutually_exclusive_markets
from .fetcher import (
    fetch_all_markets,
    fetch_event_details,
    fetch_event_details_batch,
)
from .filtering import (
    filter_markets_for_window,
    filter_markets_with_valid_strikes,
    filter_mutually_exclusive_events,
    group_markets_by_event,
    has_valid_strikes,
    is_expiring_within_window,
    validate_strikes,
)
from .types import (
    CatalogDiscoveryError,
    DiscoveredEvent,
    DiscoveredMarket,
    StrikeValidationError,
)

__all__ = [
    # Main entry point
    "discover_mutually_exclusive_markets",
    # Types
    "CatalogDiscoveryError",
    "DiscoveredEvent",
    "DiscoveredMarket",
    "StrikeValidationError",
    # Fetching
    "fetch_all_markets",
    "fetch_event_details",
    "fetch_event_details_batch",
    # Filtering
    "filter_markets_for_window",
    "filter_markets_with_valid_strikes",
    "filter_mutually_exclusive_events",
    "group_markets_by_event",
    "has_valid_strikes",
    "is_expiring_within_window",
    "validate_strikes",
]
