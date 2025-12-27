"""Tests for kalshi_catalog fetcher module."""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_catalog.fetcher import (
    _build_market_params,
    _next_cursor_or_none,
    extract_cursor,
    fetch_all_markets,
    fetch_event_details,
    fetch_event_details_batch,
)
from common.kalshi_catalog.types import CatalogDiscoveryError


class TestExtractCursor:
    """Tests for extract_cursor function."""

    def test_returns_cursor_string(self) -> None:
        """Test returns cursor when present and valid."""
        payload = {"cursor": "abc123"}
        assert extract_cursor(payload) == "abc123"

    def test_returns_none_for_missing_cursor(self) -> None:
        """Test returns None when cursor is missing."""
        payload: Dict[str, Any] = {}
        assert extract_cursor(payload) is None

    def test_returns_none_for_none_cursor(self) -> None:
        """Test returns None when cursor is None."""
        payload = {"cursor": None}
        assert extract_cursor(payload) is None

    def test_returns_none_for_non_string_cursor(self) -> None:
        """Test returns None when cursor is not a string."""
        payload = {"cursor": 123}
        assert extract_cursor(payload) is None

    def test_returns_none_for_empty_cursor(self) -> None:
        """Test returns None when cursor is empty string."""
        payload = {"cursor": ""}
        assert extract_cursor(payload) is None

    def test_returns_none_for_whitespace_cursor(self) -> None:
        """Test returns None when cursor is only whitespace."""
        payload = {"cursor": "   "}
        assert extract_cursor(payload) is None

    def test_strips_whitespace(self) -> None:
        """Test strips whitespace from cursor."""
        payload = {"cursor": "  abc123  "}
        assert extract_cursor(payload) == "abc123"


class TestBuildMarketParams:
    """Tests for _build_market_params function."""

    def test_returns_base_params(self) -> None:
        """Test returns base params without optional fields."""
        params = _build_market_params(None)
        assert params == {"status": "open", "limit": 100}

    def test_includes_cursor(self) -> None:
        """Test includes cursor when provided."""
        params = _build_market_params("cursor123")
        assert params["cursor"] == "cursor123"

    def test_includes_min_close_ts(self) -> None:
        """Test includes min_close_ts when provided."""
        params = _build_market_params(None, min_close_ts=1000)
        assert params["min_close_ts"] == "1000"

    def test_includes_max_close_ts(self) -> None:
        """Test includes max_close_ts when provided."""
        params = _build_market_params(None, max_close_ts=2000)
        assert params["max_close_ts"] == "2000"

    def test_includes_all_params(self) -> None:
        """Test includes all params when provided."""
        params = _build_market_params("cursor", min_close_ts=1000, max_close_ts=2000)
        assert params["cursor"] == "cursor"
        assert params["min_close_ts"] == "1000"
        assert params["max_close_ts"] == "2000"


class TestNextCursorOrNone:
    """Tests for _next_cursor_or_none function."""

    def test_returns_none_for_none_candidate(self) -> None:
        """Test returns None when candidate is None."""
        assert _next_cursor_or_none("prev", None) is None

    def test_returns_candidate_for_different_cursor(self) -> None:
        """Test returns candidate when different from previous."""
        assert _next_cursor_or_none("prev", "next") == "next"

    def test_raises_for_repeated_cursor(self) -> None:
        """Test raises CatalogDiscoveryError for repeated cursor."""
        with pytest.raises(CatalogDiscoveryError, match="Pagination error"):
            _next_cursor_or_none("same", "same")


class TestFetchAllMarkets:
    """Tests for fetch_all_markets function."""

    @pytest.mark.asyncio
    async def test_fetches_single_page(self) -> None:
        """Test fetches single page of markets."""
        client = AsyncMock()
        client.api_request.return_value = {
            "markets": [{"ticker": "M1"}, {"ticker": "M2"}],
            "cursor": None,
        }
        result = await fetch_all_markets(client)
        assert len(result) == 2
        assert result[0]["ticker"] == "M1"
        client.api_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetches_multiple_pages(self) -> None:
        """Test fetches multiple pages of markets."""
        client = AsyncMock()
        client.api_request.side_effect = [
            {"markets": [{"ticker": "M1"}], "cursor": "page2"},
            {"markets": [{"ticker": "M2"}], "cursor": None},
        ]
        result = await fetch_all_markets(client)
        assert len(result) == 2
        assert client.api_request.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_for_missing_markets_list(self) -> None:
        """Test raises CatalogDiscoveryError when markets list missing."""
        client = AsyncMock()
        client.api_request.return_value = {}
        with pytest.raises(CatalogDiscoveryError, match="missing 'markets' list"):
            await fetch_all_markets(client)

    @pytest.mark.asyncio
    async def test_calls_progress_callback(self) -> None:
        """Test calls progress callback during fetch."""
        client = AsyncMock()
        client.api_request.return_value = {"markets": [], "cursor": None}
        progress = MagicMock()
        await fetch_all_markets(client, progress=progress)
        progress.assert_called()

    @pytest.mark.asyncio
    async def test_passes_close_time_params(self) -> None:
        """Test passes close time params to API."""
        client = AsyncMock()
        client.api_request.return_value = {"markets": [], "cursor": None}
        await fetch_all_markets(client, min_close_ts=1000, max_close_ts=2000)
        call_args = client.api_request.call_args
        params = call_args.kwargs["params"]
        assert params["min_close_ts"] == "1000"
        assert params["max_close_ts"] == "2000"


class TestFetchEventDetails:
    """Tests for fetch_event_details function."""

    @pytest.mark.asyncio
    async def test_fetches_event_details(self) -> None:
        """Test fetches event details successfully."""
        client = AsyncMock()
        client.api_request.return_value = {
            "event": {"event_ticker": "E1", "mutually_exclusive": True},
        }
        result = await fetch_event_details(client, "E1")
        assert result is not None
        assert result["event_ticker"] == "E1"
        client.api_request.assert_called_once()
        call_args = client.api_request.call_args
        assert call_args.kwargs["path"] == "/trade-api/v2/events/E1"
        assert call_args.kwargs["params"]["with_nested_markets"] == "true"

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_event(self) -> None:
        """Test returns None when event not in response."""
        client = AsyncMock()
        client.api_request.return_value = {}
        result = await fetch_event_details(client, "E1")
        assert result is None


class TestFetchEventDetailsBatch:
    """Tests for fetch_event_details_batch function."""

    @pytest.mark.asyncio
    async def test_fetches_batch_of_events(self) -> None:
        """Test fetches batch of event details."""
        client = AsyncMock()
        client.api_request.side_effect = [
            {"event": {"event_ticker": "E1"}},
            {"event": {"event_ticker": "E2"}},
        ]
        result = await fetch_event_details_batch(client, ["E1", "E2"])
        assert len(result) == 2
        assert "E1" in result
        assert "E2" in result

    @pytest.mark.asyncio
    async def test_skips_failed_fetches(self) -> None:
        """Test skips events that fail to fetch."""
        client = AsyncMock()
        client.api_request.side_effect = [
            {"event": {"event_ticker": "E1"}},
            ValueError("fetch failed"),
        ]
        result = await fetch_event_details_batch(client, ["E1", "E2"])
        assert len(result) == 1
        assert "E1" in result

    @pytest.mark.asyncio
    async def test_skips_none_results(self) -> None:
        """Test skips events with None result."""
        client = AsyncMock()
        client.api_request.side_effect = [
            {"event": {"event_ticker": "E1"}},
            {},
        ]
        result = await fetch_event_details_batch(client, ["E1", "E2"])
        assert len(result) == 1
        assert "E1" in result

    @pytest.mark.asyncio
    async def test_calls_progress_callback(self) -> None:
        """Test calls progress callback during batch fetch."""
        client = AsyncMock()
        client.api_request.return_value = {"event": {"event_ticker": "E1"}}
        progress = MagicMock()
        await fetch_event_details_batch(client, ["E1"], progress=progress)
        progress.assert_called()
