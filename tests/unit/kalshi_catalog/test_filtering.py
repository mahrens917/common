"""Tests for kalshi_catalog filtering module."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import patch

import pytest

from common.kalshi_catalog.filtering import (
    convert_to_discovered_market,
    filter_markets_for_window,
    filter_markets_with_valid_strikes,
    filter_mutually_exclusive_events,
    group_markets_by_event,
    has_valid_strikes,
    is_expiring_within_window,
    validate_strikes,
)
from common.kalshi_catalog.types import StrikeValidationError


class TestIsExpiringWithinWindow:
    """Tests for is_expiring_within_window function."""

    def test_returns_false_for_empty_string(self) -> None:
        """Test returns False for empty close_time_str."""
        assert is_expiring_within_window("", 3600) is False

    def test_returns_false_for_invalid_datetime(self) -> None:
        """Test returns False for invalid datetime string."""
        assert is_expiring_within_window("not-a-date", 3600) is False

    def test_returns_true_for_time_within_window(self) -> None:
        """Test returns True when close time is within window."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        assert is_expiring_within_window(close_time, 3600) is True

    def test_returns_false_for_time_outside_window(self) -> None:
        """Test returns False when close time is outside window."""
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        close_time = future.isoformat()
        assert is_expiring_within_window(close_time, 3600) is False

    def test_returns_false_for_past_time(self) -> None:
        """Test returns False when close time is in the past."""
        past = datetime.now(timezone.utc) - timedelta(minutes=30)
        close_time = past.isoformat()
        assert is_expiring_within_window(close_time, 3600) is False


class TestValidateStrikes:
    """Tests for validate_strikes function."""

    def test_returns_true_for_valid_cap_strike_only(self) -> None:
        """Test returns True when only cap_strike is present."""
        market: Dict[str, Any] = {"ticker": "TEST", "cap_strike": 100.0}
        assert validate_strikes(market) is True

    def test_returns_true_for_valid_floor_strike_only(self) -> None:
        """Test returns True when only floor_strike is present."""
        market: Dict[str, Any] = {"ticker": "TEST", "floor_strike": 50.0}
        assert validate_strikes(market) is True

    def test_returns_true_for_different_strikes(self) -> None:
        """Test returns True when both strikes are different."""
        market: Dict[str, Any] = {"ticker": "TEST", "cap_strike": 100.0, "floor_strike": 50.0}
        assert validate_strikes(market) is True

    def test_raises_for_missing_both_strikes(self) -> None:
        """Test raises StrikeValidationError when both strikes missing."""
        market: Dict[str, Any] = {"ticker": "TEST"}
        with pytest.raises(StrikeValidationError, match="missing both"):
            validate_strikes(market)

    def test_raises_for_equal_strikes(self) -> None:
        """Test raises StrikeValidationError when strikes are equal."""
        market: Dict[str, Any] = {"ticker": "TEST", "cap_strike": 100.0, "floor_strike": 100.0}
        with pytest.raises(StrikeValidationError, match="equal cap_strike and floor_strike"):
            validate_strikes(market)


class TestHasValidStrikes:
    """Tests for has_valid_strikes function."""

    def test_returns_true_for_valid_strikes(self) -> None:
        """Test returns True for valid strike configuration."""
        market: Dict[str, Any] = {"ticker": "TEST", "cap_strike": 100.0}
        assert has_valid_strikes(market) is True

    def test_returns_false_for_missing_strikes(self) -> None:
        """Test returns False when both strikes missing."""
        market: Dict[str, Any] = {"ticker": "TEST"}
        assert has_valid_strikes(market) is False

    def test_returns_false_for_equal_strikes(self) -> None:
        """Test returns False when strikes are equal."""
        market: Dict[str, Any] = {"cap_strike": 100.0, "floor_strike": 100.0}
        assert has_valid_strikes(market) is False


class TestGroupMarketsByEvent:
    """Tests for group_markets_by_event function."""

    def test_groups_markets_by_event_ticker(self) -> None:
        """Test groups markets correctly by event_ticker."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        markets = [
            {"event_ticker": "E1", "close_time": close_time, "ticker": "M1"},
            {"event_ticker": "E1", "close_time": close_time, "ticker": "M2"},
            {"event_ticker": "E2", "close_time": close_time, "ticker": "M3"},
        ]
        result = group_markets_by_event(markets, 3600)
        assert len(result) == 2
        assert len(result["E1"]) == 2
        assert len(result["E2"]) == 1

    def test_filters_out_markets_without_event_ticker(self) -> None:
        """Test filters out markets missing event_ticker."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        markets = [
            {"event_ticker": "E1", "close_time": close_time},
            {"close_time": close_time},
        ]
        result = group_markets_by_event(markets, 3600)
        assert len(result) == 1
        assert "E1" in result

    def test_filters_out_markets_without_close_time(self) -> None:
        """Test filters out markets missing close_time."""
        markets = [
            {"event_ticker": "E1"},
        ]
        result = group_markets_by_event(markets, 3600)
        assert len(result) == 0

    def test_filters_out_markets_outside_window(self) -> None:
        """Test filters out markets outside expiry window."""
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        close_time = future.isoformat()
        markets = [
            {"event_ticker": "E1", "close_time": close_time},
        ]
        result = group_markets_by_event(markets, 3600)
        assert len(result) == 0


class TestFilterMutuallyExclusiveEvents:
    """Tests for filter_mutually_exclusive_events function."""

    def test_filters_to_mutually_exclusive_only(self) -> None:
        """Test filters to only mutually exclusive events."""
        events = {
            "E1": {"mutually_exclusive": True, "title": "Event 1"},
            "E2": {"mutually_exclusive": False, "title": "Event 2"},
            "E3": {"mutually_exclusive": True, "title": "Event 3"},
        }
        result = filter_mutually_exclusive_events(events)
        assert len(result) == 2
        assert "E1" in result
        assert "E3" in result
        assert "E2" not in result

    def test_handles_missing_mutually_exclusive_field(self) -> None:
        """Test handles events missing mutually_exclusive field."""
        events = {
            "E1": {"title": "Event 1"},
        }
        result = filter_mutually_exclusive_events(events)
        assert len(result) == 0


class TestFilterMarketsForWindow:
    """Tests for filter_markets_for_window function."""

    def test_returns_empty_for_non_list(self) -> None:
        """Test returns empty list for non-list input."""
        assert filter_markets_for_window(None, 3600) == []
        assert filter_markets_for_window("not a list", 3600) == []

    def test_filters_markets_within_window(self) -> None:
        """Test filters markets to those within window."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        far_future = datetime.now(timezone.utc) + timedelta(hours=2)
        far_close_time = far_future.isoformat()
        markets = [
            {"close_time": close_time, "ticker": "M1"},
            {"close_time": far_close_time, "ticker": "M2"},
        ]
        result = filter_markets_for_window(markets, 3600)
        assert len(result) == 1
        assert result[0]["ticker"] == "M1"

    def test_skips_non_dict_items(self) -> None:
        """Test skips non-dict items in list."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        markets = [
            {"close_time": close_time, "ticker": "M1"},
            "not a dict",
            None,
        ]
        result = filter_markets_for_window(markets, 3600)
        assert len(result) == 1


class TestFilterMarketsWithValidStrikes:
    """Tests for filter_markets_with_valid_strikes function."""

    def test_keeps_markets_with_valid_strikes(self) -> None:
        """Test keeps markets with valid strike configuration."""
        markets = [
            {"ticker": "M1", "cap_strike": 100.0},
            {"ticker": "M2", "floor_strike": 50.0},
            {"ticker": "M3", "cap_strike": 100.0, "floor_strike": 50.0},
        ]
        result = filter_markets_with_valid_strikes(markets)
        assert len(result) == 3

    def test_filters_out_invalid_strikes(self) -> None:
        """Test filters out markets with invalid strikes."""
        markets = [
            {"ticker": "M1", "cap_strike": 100.0},
            {"ticker": "M2"},  # Missing both strikes
            {"ticker": "M3", "cap_strike": 100.0, "floor_strike": 100.0},  # Equal strikes
        ]
        result = filter_markets_with_valid_strikes(markets)
        assert len(result) == 1
        assert result[0]["ticker"] == "M1"


class TestConvertToDiscoveredMarket:
    """Tests for convert_to_discovered_market function."""

    def test_converts_with_all_fields(self) -> None:
        """Test converts market dict with all fields."""
        market: Dict[str, Any] = {
            "ticker": "TEST-123",
            "close_time": "2024-01-01T00:00:00Z",
            "cap_strike": 100.0,
            "floor_strike": 50.0,
        }
        result = convert_to_discovered_market(market)
        assert result.ticker == "TEST-123"
        assert result.close_time == "2024-01-01T00:00:00Z"
        assert result.cap_strike == 100.0
        assert result.floor_strike == 50.0
        assert result.raw_data == market

    def test_handles_missing_ticker(self) -> None:
        """Test handles missing ticker field."""
        market: Dict[str, Any] = {"close_time": "2024-01-01T00:00:00Z"}
        result = convert_to_discovered_market(market)
        assert result.ticker == ""

    def test_handles_missing_close_time(self) -> None:
        """Test handles missing close_time field."""
        market: Dict[str, Any] = {"ticker": "TEST"}
        result = convert_to_discovered_market(market)
        assert result.close_time == ""

    def test_handles_none_strikes(self) -> None:
        """Test handles None strike values."""
        market: Dict[str, Any] = {"ticker": "TEST", "close_time": "2024-01-01T00:00:00Z"}
        result = convert_to_discovered_market(market)
        assert result.cap_strike is None
        assert result.floor_strike is None
