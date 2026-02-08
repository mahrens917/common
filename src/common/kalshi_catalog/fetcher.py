"""API fetching utilities for Kalshi market catalog discovery."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ..kalshi_api.client_helpers.errors import KalshiClientError
from .types import CatalogDiscoveryError

logger = logging.getLogger(__name__)

MAX_LIMIT = 100
MAX_CONCURRENT_REQUESTS = 10
EVENT_DETAIL_BATCH_SIZE = 100


def extract_cursor(payload: Dict[str, Any]) -> Optional[str]:
    """Extract pagination cursor from API response payload."""
    cursor = payload.get("cursor")
    if cursor is None:
        return None
    if not isinstance(cursor, str):
        return None
    stripped = cursor.strip()
    if not stripped:
        return None
    return stripped


def _build_market_params(
    cursor: Optional[str],
    *,
    min_close_ts: Optional[int] = None,
    max_close_ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Build query parameters for market fetching."""
    params: Dict[str, Any] = {"status": "open", "limit": MAX_LIMIT}
    if cursor:
        params["cursor"] = cursor
    if isinstance(min_close_ts, int):
        params["min_close_ts"] = str(min_close_ts)
    if isinstance(max_close_ts, int):
        params["max_close_ts"] = str(max_close_ts)
    return params


def _next_cursor_or_none(previous: Optional[str], candidate: Optional[str]) -> Optional[str]:
    """Get next cursor, raising if repeated (pagination error)."""
    if candidate is None:
        return None
    if candidate == previous:
        raise CatalogDiscoveryError(f"Pagination error: received repeated cursor '{candidate}'")
    return candidate


async def fetch_all_markets(
    client: Any,
    *,
    min_close_ts: Optional[int] = None,
    max_close_ts: Optional[int] = None,
    progress: Callable[[str], None] | None = None,
) -> List[Dict[str, Any]]:
    """Fetch all open markets from Kalshi API with pagination.

    Args:
        client: Kalshi API client with api_request method
        min_close_ts: Optional minimum close timestamp filter
        max_close_ts: Optional maximum close timestamp filter
        progress: Optional progress callback

    Returns:
        List of market dictionaries
    """
    markets: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    page_number = 0
    start_time = datetime.now(timezone.utc)

    while True:
        page_number += 1
        logger.info("Fetching markets page %d", page_number)
        if progress:
            progress(f"markets_page={page_number} total={len(markets)}")

        params = _build_market_params(
            cursor,
            min_close_ts=min_close_ts,
            max_close_ts=max_close_ts,
        )

        response = await client.api_request(
            method="GET",
            path="/trade-api/v2/markets",
            params=params,
            operation_name="fetch_markets_for_catalog",
        )

        page_markets = response.get("markets")
        if not isinstance(page_markets, list):
            raise CatalogDiscoveryError("Markets response missing 'markets' list")

        markets.extend(page_markets)
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            "Fetched page %d: +%d markets (total=%d, elapsed=%.1fs)",
            page_number,
            len(page_markets),
            len(markets),
            elapsed,
        )

        cursor = _next_cursor_or_none(cursor, extract_cursor(response))
        if cursor is None:
            break

    return markets


async def fetch_event_details(client: Any, event_ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch event details including mutually_exclusive flag and nested markets."""
    response = await client.api_request(
        method="GET",
        path=f"/trade-api/v2/events/{event_ticker}",
        params={"with_nested_markets": "true"},
        operation_name="fetch_event_details",
    )
    return response.get("event")


async def _fetch_with_semaphore(
    semaphore: asyncio.Semaphore,
    client: Any,
    ticker: str,
) -> tuple[str, Optional[Dict[str, Any]], Optional[Exception]]:
    """Fetch event details with semaphore to limit concurrency."""
    async with semaphore:
        try:
            result = await fetch_event_details(client, ticker)
        except (ValueError, KeyError, RuntimeError, KalshiClientError) as exc:  # policy_guard: allow-silent-handler
            logger.warning("Failed to fetch event %s: %s", ticker, exc)
            return (ticker, None, exc)
        else:
            return (ticker, result, None)


async def fetch_event_details_batch(
    client: Any,
    event_tickers: List[str],
    *,
    progress: Callable[[str], None] | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Fetch event details for multiple events with concurrency control.

    Args:
        client: Kalshi API client with api_request method
        event_tickers: List of event tickers to fetch
        progress: Optional progress callback

    Returns:
        Dict mapping event_ticker to event details (excludes failed fetches)
    """
    results: Dict[str, Dict[str, Any]] = {}
    total = len(event_tickers)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    for batch_start in range(0, total, EVENT_DETAIL_BATCH_SIZE):
        batch = event_tickers[batch_start : batch_start + EVENT_DETAIL_BATCH_SIZE]
        batch_end = batch_start + len(batch)
        logger.info("Fetching event details batch (%d-%d/%d)", batch_start + 1, batch_end, total)
        if progress:
            progress(f"event_details={batch_end}/{total}")

        tasks = [_fetch_with_semaphore(semaphore, client, ticker) for ticker in batch]
        batch_results = await asyncio.gather(*tasks)

        for ticker, event_data, error in batch_results:
            if error is None and event_data is not None:
                results[ticker] = event_data

    return results


__all__ = [
    "EVENT_DETAIL_BATCH_SIZE",
    "MAX_CONCURRENT_REQUESTS",
    "MAX_LIMIT",
    "extract_cursor",
    "fetch_all_markets",
    "fetch_event_details",
    "fetch_event_details_batch",
]
