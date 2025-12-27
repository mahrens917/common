"""Tests for kalshi_catalog discovery module."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.kalshi_catalog.discovery import (
    _process_all_events,
    _process_event,
    _report_progress,
    discover_mutually_exclusive_markets,
)
from common.kalshi_catalog.types import CatalogDiscoveryError


class TestReportProgress:
    """Tests for _report_progress helper."""

    def test_calls_callback_when_provided(self) -> None:
        """Test calls callback when provided."""
        callback = MagicMock()
        _report_progress(callback, "test message")
        callback.assert_called_once_with("test message")

    def test_does_nothing_when_callback_none(self) -> None:
        """Test does nothing when callback is None."""
        _report_progress(None, "test message")


class TestProcessEvent:
    """Tests for _process_event function."""

    def test_processes_valid_event(self) -> None:
        """Test processes a valid mutually exclusive event."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        details: Dict[str, Any] = {
            "mutually_exclusive": True,
            "title": "Test Event",
            "category": "Crypto",
            "markets": [
                {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0},
                {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0},
            ],
        }
        result = _process_event("E1", details, 3600, 2)
        assert result.event_ticker == "E1"
        assert result.title == "Test Event"
        assert result.category == "Crypto"
        assert result.mutually_exclusive is True
        assert len(result.markets) == 2

    def test_raises_for_non_dict_details(self) -> None:
        """Test raises TypeError for non-dict details."""
        with pytest.raises(TypeError, match="is not a dict"):
            _process_event("E1", "not a dict", 3600, 2)

    def test_raises_for_non_mutually_exclusive(self) -> None:
        """Test raises ValueError for non-mutually exclusive event."""
        details: Dict[str, Any] = {"mutually_exclusive": False, "title": "Test"}
        with pytest.raises(ValueError, match="not mutually exclusive"):
            _process_event("E1", details, 3600, 2)

    def test_raises_for_missing_title(self) -> None:
        """Test raises CatalogDiscoveryError for missing title."""
        details: Dict[str, Any] = {"mutually_exclusive": True}
        with pytest.raises(CatalogDiscoveryError, match="missing title"):
            _process_event("E1", details, 3600, 2)

    def test_uses_default_category(self) -> None:
        """Test uses default category when not provided."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        details: Dict[str, Any] = {
            "mutually_exclusive": True,
            "title": "Test",
            "markets": [
                {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0},
                {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0},
            ],
        }
        result = _process_event("E1", details, 3600, 2)
        assert result.category == "Unknown"

    def test_raises_for_insufficient_markets(self) -> None:
        """Test raises ValueError when fewer markets than minimum."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        details: Dict[str, Any] = {
            "mutually_exclusive": True,
            "title": "Test",
            "markets": [{"ticker": "M1", "close_time": close_time, "cap_strike": 100.0}],
        }
        with pytest.raises(ValueError, match="minimum required"):
            _process_event("E1", details, 3600, 2)


class TestProcessAllEvents:
    """Tests for _process_all_events function."""

    def test_processes_valid_events(self) -> None:
        """Test processes valid events successfully."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        events = {
            "E1": {
                "mutually_exclusive": True,
                "title": "Event 1",
                "markets": [
                    {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0},
                    {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0},
                ],
            },
        }
        result = _process_all_events(events, 3600, 2)
        assert len(result) == 1
        assert result[0].event_ticker == "E1"

    def test_skips_invalid_events(self) -> None:
        """Test skips events that fail validation."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        events = {
            "E1": {
                "mutually_exclusive": True,
                "title": "Event 1",
                "markets": [
                    {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0},
                    {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0},
                ],
            },
            "E2": {"mutually_exclusive": False, "title": "Event 2"},
        }
        result = _process_all_events(events, 3600, 2)
        assert len(result) == 1
        assert result[0].event_ticker == "E1"


class TestDiscoverMutuallyExclusiveMarkets:
    """Tests for discover_mutually_exclusive_markets function."""

    @pytest.mark.asyncio
    async def test_discovers_mutually_exclusive_markets(self) -> None:
        """Test discovers mutually exclusive markets end-to-end."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        client = AsyncMock()
        client.api_request.side_effect = [
            {
                "markets": [
                    {"ticker": "M1", "event_ticker": "E1", "close_time": close_time},
                    {"ticker": "M2", "event_ticker": "E1", "close_time": close_time},
                ],
                "cursor": None,
            },
            {
                "event": {
                    "event_ticker": "E1",
                    "mutually_exclusive": True,
                    "title": "Test Event",
                    "markets": [
                        {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0},
                        {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0},
                    ],
                },
            },
        ]
        result = await discover_mutually_exclusive_markets(
            client,
            expiry_window_seconds=3600,
            min_markets_per_event=2,
        )
        assert len(result) == 1
        assert result[0].event_ticker == "E1"
        assert len(result[0].markets) == 2

    @pytest.mark.asyncio
    async def test_filters_non_mutually_exclusive_events(self) -> None:
        """Test filters out non-mutually exclusive events."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        client = AsyncMock()
        client.api_request.side_effect = [
            {
                "markets": [{"ticker": "M1", "event_ticker": "E1", "close_time": close_time}],
                "cursor": None,
            },
            {"event": {"event_ticker": "E1", "mutually_exclusive": False, "title": "Test"}},
        ]
        result = await discover_mutually_exclusive_markets(
            client,
            expiry_window_seconds=3600,
            min_markets_per_event=1,
        )
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_calls_progress_callback(self) -> None:
        """Test calls progress callback during discovery."""
        client = AsyncMock()
        client.api_request.return_value = {"markets": [], "cursor": None}
        progress = MagicMock()
        await discover_mutually_exclusive_markets(
            client,
            expiry_window_seconds=3600,
            progress=progress,
        )
        assert progress.call_count >= 1

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_markets(self) -> None:
        """Test returns empty list when no markets found."""
        client = AsyncMock()
        client.api_request.return_value = {"markets": [], "cursor": None}
        result = await discover_mutually_exclusive_markets(
            client,
            expiry_window_seconds=3600,
        )
        assert result == []
