"""Main discovery orchestration for Kalshi market catalog."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List

from .fetcher import fetch_all_markets, fetch_event_details_batch
from .filtering import (
    SkippedMarketStats,
    convert_to_discovered_market,
    filter_markets_for_window,
    filter_mutually_exclusive_events,
    group_markets_by_event,
    sort_markets_by_strike,
)
from .types import CatalogDiscoveryError, DiscoveredEvent, SkippedMarketsInfo

logger = logging.getLogger(__name__)


DiscoveryResult = tuple[List[DiscoveredEvent], SkippedMarketsInfo]

DEFAULT_CATEGORY = "Unknown"
MAX_TICKERS_TO_DISPLAY = 5


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
    5. Filters markets within the time window
    6. Validates minimum markets per event

    Args:
        client: Kalshi API client with api_request method
        expiry_window_seconds: Maximum seconds from now for market expiry
        min_markets_per_event: Minimum number of valid markets required per event
        progress: Optional progress callback

    Returns:
        List of DiscoveredEvent objects with validated markets
    """
    now_ts = int(time.time())
    max_ts = now_ts + expiry_window_seconds if expiry_window_seconds > 0 else None

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

    # Step 5-6: Process each event
    skipped_stats = SkippedMarketStats()
    discovered = _process_all_events(
        mutually_exclusive_events,
        expiry_window_seconds,
        min_markets_per_event,
        skipped_stats,
    )

    # Final summary
    market_count = sum(len(event.markets) for event in discovered)
    _report_progress(progress, f"phase=done events={len(discovered)} markets={market_count}")
    logger.info("Total: %d mutually exclusive events with %d valid markets", len(discovered), market_count)

    _log_skipped_stats(skipped_stats)
    return discovered


async def discover_with_skipped_stats(
    client: Any,
    *,
    expiry_window_seconds: int,
    min_markets_per_event: int = 2,
    progress: Callable[[str], None] | None = None,
) -> DiscoveryResult:
    """Discover markets and return both events and skipped market stats.

    Same as discover_mutually_exclusive_markets but also returns information
    about markets that were skipped due to unsupported strike types.

    Args:
        client: Kalshi API client with api_request method
        expiry_window_seconds: Maximum seconds from now for market expiry
        min_markets_per_event: Minimum number of valid markets required per event
        progress: Optional progress callback

    Returns:
        Tuple of (discovered events, skipped market info)
    """
    now_ts = int(time.time())
    max_ts = now_ts + expiry_window_seconds if expiry_window_seconds > 0 else None

    logger.info("Fetching all open markets (window=%ss)...", expiry_window_seconds)
    _report_progress(progress, "phase=fetch_markets")
    markets = await fetch_all_markets(
        client,
        min_close_ts=now_ts,
        max_close_ts=max_ts,
        progress=progress,
    )
    logger.info("Fetched %d markets total", len(markets))

    event_market_groups = group_markets_by_event(markets, expiry_window_seconds)
    unique_events = list(event_market_groups.keys())
    logger.info("Found %d unique events from markets", len(unique_events))

    _report_progress(progress, f"phase=fetch_event_details total={len(unique_events)}")
    event_details = await fetch_event_details_batch(client, unique_events, progress=progress)
    logger.info("Fetched details for %d events", len(event_details))

    mutually_exclusive_events = filter_mutually_exclusive_events(event_details)
    logger.info(
        "Found %d mutually exclusive events (filtered from %d)",
        len(mutually_exclusive_events),
        len(event_details),
    )

    skipped_stats = SkippedMarketStats()
    discovered = _process_all_events(
        mutually_exclusive_events,
        expiry_window_seconds,
        min_markets_per_event,
        skipped_stats,
    )

    market_count = sum(len(event.markets) for event in discovered)
    _report_progress(progress, f"phase=done events={len(discovered)} markets={market_count}")
    logger.info("Total: %d mutually exclusive events with %d valid markets", len(discovered), market_count)

    _log_skipped_stats(skipped_stats)

    skipped_info = SkippedMarketsInfo(
        total_skipped=skipped_stats.total_skipped,
        by_strike_type=dict(skipped_stats.by_strike_type),
        by_category=dict(skipped_stats.by_category),
    )

    return discovered, skipped_info


def _process_all_events(
    events: Dict[str, Dict[str, Any]],
    expiry_window_seconds: int,
    min_markets_per_event: int,
    skipped_stats: SkippedMarketStats,
) -> List[DiscoveredEvent]:
    """Process all events and return valid DiscoveredEvent instances."""
    discovered: List[DiscoveredEvent] = []
    for event_ticker, details in events.items():
        try:
            event = _process_event(event_ticker, details, expiry_window_seconds, min_markets_per_event, skipped_stats)
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
    skipped_stats: SkippedMarketStats,
) -> DiscoveredEvent:
    """Process a single event into a DiscoveredEvent.

    Args:
        event_ticker: The event ticker
        details: Event details from API
        expiry_window_seconds: Maximum seconds from now for market expiry
        min_markets_per_event: Minimum number of valid markets required
        skipped_stats: Stats collector for skipped markets

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
    markets_in_window = filter_markets_for_window(nested_markets, expiry_window_seconds, skipped_stats)

    # Step 6: Validate minimum markets per event
    if len(markets_in_window) < min_markets_per_event:
        raise ValueError(f"Event {event_ticker} has {len(markets_in_window)} markets, " f"minimum required is {min_markets_per_event}")

    # Convert to DiscoveredMarket instances and sort by strike
    discovered_markets = [convert_to_discovered_market(m) for m in markets_in_window]
    discovered_markets = sort_markets_by_strike(discovered_markets)

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


def _get_ellipsis_suffix(items: List[str]) -> str:
    """Return ellipsis suffix if list exceeds display limit."""
    if len(items) > MAX_TICKERS_TO_DISPLAY:
        return "..."
    return ""


def _log_skipped_stats(skipped_stats: SkippedMarketStats) -> None:
    """Log summary of skipped markets."""
    if skipped_stats.total_skipped == 0:
        return
    logger.warning("Skipped %d markets with unsupported strike types", skipped_stats.total_skipped)
    for strike_type, tickers in sorted(skipped_stats.by_strike_type.items()):
        display = ", ".join(tickers[:MAX_TICKERS_TO_DISPLAY])
        suffix = _get_ellipsis_suffix(tickers)
        logger.warning("  strike_type='%s': %d markets (%s%s)", strike_type, len(tickers), display, suffix)
    for category, count in sorted(skipped_stats.by_category.items(), key=lambda x: -x[1]):
        logger.warning("  category='%s': %d markets skipped", category, count)


__all__ = [
    "DiscoveryResult",
    "discover_mutually_exclusive_markets",
    "discover_with_skipped_stats",
]
