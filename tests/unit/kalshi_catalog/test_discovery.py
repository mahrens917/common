"""Tests for kalshi_catalog discovery module."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_catalog.discovery import (
    _log_skipped_stats,
    _process_all_events,
    _process_event,
    _report_progress,
    discover_with_skipped_stats,
)
from common.kalshi_catalog.filtering import SkippedMarketStats
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

    def test_processes_valid_me_event(self) -> None:
        """Test processes a valid mutually exclusive event."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        details: Dict[str, Any] = {
            "mutually_exclusive": True,
            "title": "Test Event",
            "category": "Crypto",
            "markets": [
                {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0, "strike_type": "less"},
                {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0, "strike_type": "greater"},
            ],
        }
        stats = SkippedMarketStats()
        result = _process_event("E1", details, 3600, 2, stats)
        assert result.event_ticker == "E1"
        assert result.title == "Test Event"
        assert result.category == "Crypto"
        assert result.mutually_exclusive is True
        assert len(result.markets) == 2

    def test_processes_valid_non_me_event(self) -> None:
        """Test processes a valid non-mutually exclusive event."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        details: Dict[str, Any] = {
            "mutually_exclusive": False,
            "title": "Test Event",
            "category": "Crypto",
            "markets": [
                {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0, "strike_type": "less"},
                {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0, "strike_type": "greater"},
            ],
        }
        stats = SkippedMarketStats()
        result = _process_event("E1", details, 3600, 2, stats)
        assert result.event_ticker == "E1"
        assert result.mutually_exclusive is False
        assert len(result.markets) == 2

    def test_raises_for_non_dict_details(self) -> None:
        """Test raises TypeError for non-dict details."""
        stats = SkippedMarketStats()
        with pytest.raises(TypeError, match="is not a dict"):
            _process_event("E1", "not a dict", 3600, 2, stats)

    def test_raises_for_missing_title(self) -> None:
        """Test raises CatalogDiscoveryError for missing title."""
        details: Dict[str, Any] = {}
        stats = SkippedMarketStats()
        with pytest.raises(CatalogDiscoveryError, match="missing title"):
            _process_event("E1", details, 3600, 2, stats)

    def test_uses_default_category(self) -> None:
        """Test uses default category when not provided."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        details: Dict[str, Any] = {
            "mutually_exclusive": True,
            "title": "Test",
            "markets": [
                {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0, "strike_type": "less"},
                {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0, "strike_type": "greater"},
            ],
        }
        stats = SkippedMarketStats()
        result = _process_event("E1", details, 3600, 2, stats)
        assert result.category == "Unknown"

    def test_raises_for_insufficient_markets(self) -> None:
        """Test raises ValueError when fewer markets than minimum."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        details: Dict[str, Any] = {
            "mutually_exclusive": True,
            "title": "Test",
            "markets": [{"ticker": "M1", "close_time": close_time, "cap_strike": 100.0, "strike_type": "less"}],
        }
        stats = SkippedMarketStats()
        with pytest.raises(ValueError, match="minimum required"):
            _process_event("E1", details, 3600, 2, stats)


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
                    {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0, "strike_type": "less"},
                    {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0, "strike_type": "greater"},
                ],
            },
        }
        stats = SkippedMarketStats()
        result = _process_all_events(events, 3600, 2, stats)
        assert len(result) == 1
        assert result[0].event_ticker == "E1"

    def test_skips_events_with_insufficient_markets(self) -> None:
        """Test skips events that fail validation due to insufficient markets."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        events = {
            "E1": {
                "mutually_exclusive": True,
                "title": "Event 1",
                "markets": [
                    {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0, "strike_type": "less"},
                    {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0, "strike_type": "greater"},
                ],
            },
            "E2": {
                "mutually_exclusive": False,
                "title": "Event 2",
                "markets": [{"ticker": "M3", "close_time": close_time, "strike_type": "less"}],
            },
        }
        stats = SkippedMarketStats()
        result = _process_all_events(events, 3600, 2, stats)
        assert len(result) == 1
        assert result[0].event_ticker == "E1"


class TestDiscoverWithSkippedStats:
    """Tests for discover_with_skipped_stats function."""

    @pytest.mark.asyncio
    async def test_returns_events_and_skipped_stats(self) -> None:
        """Test returns both discovered events and skipped market stats."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        client = AsyncMock()
        client.api_request.side_effect = [
            {
                "markets": [
                    {"ticker": "M1", "event_ticker": "E1", "close_time": close_time, "strike_type": "less"},
                    {"ticker": "M2", "event_ticker": "E1", "close_time": close_time, "strike_type": "greater"},
                ],
                "cursor": None,
            },
            {
                "event": {
                    "event_ticker": "E1",
                    "mutually_exclusive": True,
                    "title": "Test Event",
                    "markets": [
                        {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0, "strike_type": "less"},
                        {"ticker": "M2", "close_time": close_time, "floor_strike": 50.0, "strike_type": "greater"},
                    ],
                },
            },
        ]
        events, skipped_info = await discover_with_skipped_stats(
            client,
            expiry_window_seconds=3600,
            min_markets_per_event=2,
        )
        assert len(events) == 1
        assert events[0].event_ticker == "E1"
        assert skipped_info.total_skipped == 0

    @pytest.mark.asyncio
    async def test_returns_skipped_info_for_unsupported_types(self) -> None:
        """Test returns skipped info for markets with unsupported strike types."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        client = AsyncMock()
        client.api_request.side_effect = [
            {
                "markets": [
                    {"ticker": "M1", "event_ticker": "E1", "close_time": close_time, "strike_type": "less"},
                    {"ticker": "M2", "event_ticker": "E1", "close_time": close_time, "strike_type": "unsupported"},
                ],
                "cursor": None,
            },
            {
                "event": {
                    "event_ticker": "E1",
                    "mutually_exclusive": True,
                    "title": "Test Event",
                    "markets": [
                        {"ticker": "M1", "close_time": close_time, "cap_strike": 100.0, "strike_type": "less"},
                        {
                            "ticker": "M2",
                            "close_time": close_time,
                            "floor_strike": 50.0,
                            "strike_type": "unsupported",
                            "category": "Crypto",
                        },
                        {"ticker": "M3", "close_time": close_time, "floor_strike": 75.0, "strike_type": "greater"},
                    ],
                },
            },
        ]
        events, skipped_info = await discover_with_skipped_stats(
            client,
            expiry_window_seconds=3600,
            min_markets_per_event=2,
        )
        assert len(events) == 1
        assert skipped_info.total_skipped == 1
        assert "unsupported" in skipped_info.by_strike_type

    @pytest.mark.asyncio
    async def test_calls_progress_callback(self) -> None:
        """Test calls progress callback during discovery."""
        client = AsyncMock()
        client.api_request.return_value = {"markets": [], "cursor": None}
        progress = MagicMock()
        await discover_with_skipped_stats(
            client,
            expiry_window_seconds=3600,
            progress=progress,
        )
        assert progress.call_count >= 1


class TestLogSkippedStats:
    """Tests for _log_skipped_stats helper function."""

    def test_does_nothing_when_no_skipped(self) -> None:
        """Test does nothing when no markets were skipped."""
        stats = SkippedMarketStats()
        _log_skipped_stats(stats)

    def test_logs_skipped_stats_with_data(self, caplog) -> None:
        """Test logs skipped stats when markets were skipped."""
        import logging

        stats = SkippedMarketStats()
        stats.add_skipped("M1", "unsupported", "Crypto")
        stats.add_skipped("M2", "unsupported", "Weather")
        stats.add_skipped("M3", "missing", "Weather")

        with caplog.at_level(logging.INFO):
            _log_skipped_stats(stats)

        assert "Skipped 3 markets" in caplog.text
        assert "unsupported" in caplog.text
        assert "missing" in caplog.text

    def test_truncates_long_ticker_lists(self, caplog) -> None:
        """Test truncates ticker lists when more than MAX_TICKERS_TO_DISPLAY."""
        import logging

        stats = SkippedMarketStats()
        for i in range(10):
            stats.add_skipped(f"M{i}", "unsupported", "Crypto")

        with caplog.at_level(logging.INFO):
            _log_skipped_stats(stats)

        assert "..." in caplog.text
        assert "10 markets" in caplog.text
