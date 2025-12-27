"""Main discovery orchestration for Kalshi market catalog."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List

from .fetcher import fetch_all_markets, fetch_event_details_batch
from .filtering import (
    convert_to_discovered_market,
    filter_markets_for_window,
    filter_markets_with_valid_strikes,
    filter_mutually_exclusive_events,
    group_markets_by_event,
)
from .types import CatalogDiscoveryError, DiscoveredEvent

logger = logging.getLogger(__name__)

DEFAULT_CATEGORY = "Unknown"


async def discover_mutually_exclusive_markets(
    client: Any,
    *,
    expiry_window_seconds: int,
    min_markets_per_event: int = 2,
    progress: Callable[[str], None] | None = None,
) -> List[DiscoveredEvent]:
    """Discover all mutually exclusive events with valid markets.

    This is the main entry point for market discovery. It:
    1. Fetches all open markets within the expiry window
    2. Groups markets by event_ticker
    3. Fetches event details for each unique event
    4. Filters to only mutually_exclusive events
    5. Validates strike prices (cap_strike/floor_strike)
    6. Filters markets within the time window
    7. Validates minimum markets per event

    Args:
        client: Kalshi API client with api_request method
        expiry_window_seconds: Maximum seconds from now for market expiry
        min_markets_per_event: Minimum number of valid markets required per event
        progress: Optional progress callback

    Returns:
        List of DiscoveredEvent objects with validated markets
    """
    now_ts = int(time.time())
    max_ts = now_ts + expiry_window_seconds

    # Step 1: Fetch all open markets with time window
    logger.info("Fetching all open markets (window=%ss)...", expiry_window_seconds)
    _report_progress(progress, "phase=fetch_markets")
    markets = await fetch_all_markets(
        client,
        min_close_ts=now_ts,
        max_close_ts=max_ts,
        progress=progress,
    )
    logger.info("Fetched %d markets total", len(markets))

    # Step 2: Group markets by event_ticker
    event_market_groups = group_markets_by_event(markets, expiry_window_seconds)
    unique_events = list(event_market_groups.keys())
    logger.info("Found %d unique events from markets", len(unique_events))

    # Step 3: Fetch event details for each unique event
    _report_progress(progress, f"phase=fetch_event_details total={len(unique_events)}")
    event_details = await fetch_event_details_batch(client, unique_events, progress=progress)
    logger.info("Fetched details for %d events", len(event_details))

    # Step 4: Filter to only mutually_exclusive events
    mutually_exclusive_events = filter_mutually_exclusive_events(event_details)
    logger.info(
        "Found %d mutually exclusive events (filtered from %d)",
        len(mutually_exclusive_events),
        len(event_details),
    )

    # Step 5-7: Process each event
    discovered = _process_all_events(
        mutually_exclusive_events,
        expiry_window_seconds,
        min_markets_per_event,
    )

    # Final summary
    market_count = sum(len(event.markets) for event in discovered)
    _report_progress(progress, f"phase=done events={len(discovered)} markets={market_count}")
    logger.info("Total: %d mutually exclusive events with %d valid markets", len(discovered), market_count)
    return discovered


def _process_all_events(
    events: Dict[str, Dict[str, Any]],
    expiry_window_seconds: int,
    min_markets_per_event: int,
) -> List[DiscoveredEvent]:
    """Process all events and return valid DiscoveredEvent instances."""
    discovered: List[DiscoveredEvent] = []
    for event_ticker, details in events.items():
        try:
            event = _process_event(event_ticker, details, expiry_window_seconds, min_markets_per_event)
        except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
            logger.debug("Skipping event %s: %s", event_ticker, exc)
            continue
        discovered.append(event)
        logger.info("Discovered mutually exclusive event: %s (%d markets)", event_ticker, len(event.markets))
    return discovered


def _process_event(
    event_ticker: str,
    details: Dict[str, Any],
    expiry_window_seconds: int,
    min_markets_per_event: int,
) -> DiscoveredEvent:
    """Process a single event into a DiscoveredEvent.

    Args:
        event_ticker: The event ticker
        details: Event details from API
        expiry_window_seconds: Maximum seconds from now for market expiry
        min_markets_per_event: Minimum number of valid markets required

    Returns:
        DiscoveredEvent with validated markets

    Raises:
        TypeError: If event details are invalid
        ValueError: If event doesn't meet criteria
    """
    if not isinstance(details, dict):
        raise TypeError(f"Event details for {event_ticker} is not a dict: {type(details).__name__}")

    if details.get("mutually_exclusive") is not True:
        raise ValueError(f"Event {event_ticker} is not mutually exclusive")

    title_value = details.get("title")
    if title_value is None:
        raise CatalogDiscoveryError(f"Event {event_ticker} missing title field")
    title = str(title_value)

    category_value = details.get("category")
    category = DEFAULT_CATEGORY
    if category_value is not None:
        category = str(category_value)

    # Step 5: Filter markets within time window
    nested_markets = details.get("markets")
    markets_in_window = filter_markets_for_window(nested_markets, expiry_window_seconds)

    # Step 6: Validate strike prices
    valid_markets = filter_markets_with_valid_strikes(markets_in_window)

    # Step 7: Validate minimum markets per event
    if len(valid_markets) < min_markets_per_event:
        raise ValueError(f"Event {event_ticker} has {len(valid_markets)} valid markets, " f"minimum required is {min_markets_per_event}")

    # Convert to DiscoveredMarket instances
    discovered_markets = [convert_to_discovered_market(m) for m in valid_markets]

    return DiscoveredEvent(
        event_ticker=event_ticker,
        title=title,
        category=category,
        mutually_exclusive=True,
        markets=discovered_markets,
    )


def _report_progress(progress: Callable[[str], None] | None, message: str) -> None:
    """Report progress if callback is provided."""
    if progress:
        progress(message)


__all__ = [
    "discover_mutually_exclusive_markets",
]
