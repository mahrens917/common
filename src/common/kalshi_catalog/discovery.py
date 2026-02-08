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
    group_markets_by_event,
    sort_markets_by_strike,
)
from .types import CatalogDiscoveryError, DiscoveredEvent, SkippedMarketsInfo

logger = logging.getLogger(__name__)


DEFAULT_CATEGORY = "Unknown"
MAX_TICKERS_TO_DISPLAY = 5


async def discover_with_skipped_stats(
    client: Any,
    *,
    expiry_window_seconds: int,
    min_markets_per_event: int = 2,
    progress: Callable[[str], None] | None = None,
) -> tuple[List[DiscoveredEvent], SkippedMarketsInfo]:
    """Discover all events with valid markets and skipped market stats.

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

    skipped_stats = SkippedMarketStats()
    discovered = _process_all_events(
        event_details,
        expiry_window_seconds,
        min_markets_per_event,
        skipped_stats,
    )

    market_count = sum(len(event.markets) for event in discovered)
    _report_progress(progress, f"phase=done events={len(discovered)} markets={market_count}")
    logger.info("Total: %d events with %d valid markets", len(discovered), market_count)

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
        logger.info("Discovered event: %s (%d markets, ME=%s)", event_ticker, len(event.markets), event.mutually_exclusive)
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
        ValueError: If event doesn't have enough markets
    """
    if not isinstance(details, dict):
        raise TypeError(f"Event details for {event_ticker} is not a dict: {type(details).__name__}")

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
        mutually_exclusive=details.get("mutually_exclusive") is True,
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
    logger.info("Skipped %d markets total", skipped_stats.total_skipped)
    if skipped_stats.by_zero_volume > 0:
        logger.info("  zero volume: %d markets", skipped_stats.by_zero_volume)
    for strike_type, tickers in sorted(skipped_stats.by_strike_type.items()):
        display = ", ".join(tickers[:MAX_TICKERS_TO_DISPLAY])
        suffix = _get_ellipsis_suffix(tickers)
        logger.info("  strike_type='%s': %d markets (%s%s)", strike_type, len(tickers), display, suffix)
    for category, count in sorted(skipped_stats.by_category.items(), key=lambda x: -x[1]):
        logger.info("  category='%s': %d markets skipped", category, count)


__all__ = [
    "discover_with_skipped_stats",
]
