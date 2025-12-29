"""Tests for kalshi_catalog filtering module."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from common.kalshi_catalog.filtering import (
    compute_effective_strike,
    convert_to_discovered_market,
    filter_markets_for_window,
    filter_mutually_exclusive_events,
    group_markets_by_event,
    is_expiring_within_window,
    sort_markets_by_strike,
)
from common.kalshi_catalog.types import DiscoveredMarket


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
            {"close_time": close_time, "ticker": "M1", "strike_type": "greater"},
            {"close_time": far_close_time, "ticker": "M2", "strike_type": "greater"},
        ]
        result = filter_markets_for_window(markets, 3600)
        assert len(result) == 1
        assert result[0]["ticker"] == "M1"

    def test_skips_non_dict_items(self) -> None:
        """Test skips non-dict items in list."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        markets = [
            {"close_time": close_time, "ticker": "M1", "strike_type": "less"},
            "not a dict",
            None,
        ]
        result = filter_markets_for_window(markets, 3600)
        assert len(result) == 1

    def test_allows_all_supported_strike_types(self) -> None:
        """Test allows all supported strike types including custom/functional/structured."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        markets = [
            {"close_time": close_time, "ticker": "M1", "strike_type": "greater"},
            {"close_time": close_time, "ticker": "M2", "strike_type": "custom"},
            {"close_time": close_time, "ticker": "M3", "strike_type": "functional"},
            {"close_time": close_time, "ticker": "M4", "strike_type": "structured"},
            {"close_time": close_time, "ticker": "M5", "strike_type": "between"},
        ]
        result = filter_markets_for_window(markets, 3600)
        assert len(result) == 5
        tickers = [m["ticker"] for m in result]
        assert "M1" in tickers
        assert "M2" in tickers
        assert "M3" in tickers
        assert "M4" in tickers
        assert "M5" in tickers

    def test_filters_out_missing_strike_type(self) -> None:
        """Test filters out markets without strike_type field."""
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        close_time = future.isoformat()
        markets = [
            {"close_time": close_time, "ticker": "M1", "strike_type": "greater"},
            {"close_time": close_time, "ticker": "M2"},
        ]
        result = filter_markets_for_window(markets, 3600)
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


class TestComputeEffectiveStrike:
    """Tests for compute_effective_strike function."""

    def test_returns_average_when_both_strikes_present(self) -> None:
        """Test returns average of cap and floor when both present."""
        market = DiscoveredMarket(
            ticker="TEST",
            close_time="2024-01-01T00:00:00Z",
            cap_strike=100.0,
            floor_strike=50.0,
            raw_data={},
        )
        result = compute_effective_strike(market)
        assert result == 75.0

    def test_returns_cap_when_only_cap_present(self) -> None:
        """Test returns cap strike when only cap is present."""
        market = DiscoveredMarket(
            ticker="TEST",
            close_time="2024-01-01T00:00:00Z",
            cap_strike=100.0,
            floor_strike=None,
            raw_data={},
        )
        result = compute_effective_strike(market)
        assert result == 100.0

    def test_returns_floor_when_only_floor_present(self) -> None:
        """Test returns floor strike when only floor is present."""
        market = DiscoveredMarket(
            ticker="TEST",
            close_time="2024-01-01T00:00:00Z",
            cap_strike=None,
            floor_strike=50.0,
            raw_data={},
        )
        result = compute_effective_strike(market)
        assert result == 50.0

    def test_returns_inf_when_no_strikes(self) -> None:
        """Test returns inf when neither strike is present."""
        market = DiscoveredMarket(
            ticker="TEST",
            close_time="2024-01-01T00:00:00Z",
            cap_strike=None,
            floor_strike=None,
            raw_data={},
        )
        result = compute_effective_strike(market)
        assert result == float("inf")

    def test_ignores_zero_cap_strike(self) -> None:
        """Test treats zero cap strike as invalid."""
        market = DiscoveredMarket(
            ticker="TEST",
            close_time="2024-01-01T00:00:00Z",
            cap_strike=0,
            floor_strike=50.0,
            raw_data={},
        )
        result = compute_effective_strike(market)
        assert result == 50.0

    def test_ignores_zero_floor_strike(self) -> None:
        """Test treats zero floor strike as invalid."""
        market = DiscoveredMarket(
            ticker="TEST",
            close_time="2024-01-01T00:00:00Z",
            cap_strike=100.0,
            floor_strike=0,
            raw_data={},
        )
        result = compute_effective_strike(market)
        assert result == 100.0


class TestSortMarketsByStrike:
    """Tests for sort_markets_by_strike function."""

    def test_sorts_by_effective_strike_ascending(self) -> None:
        """Test markets are sorted by strike value ascending."""
        markets = [
            DiscoveredMarket(ticker="M3", close_time="", cap_strike=None, floor_strike=150.0, raw_data={}),
            DiscoveredMarket(ticker="M1", close_time="", cap_strike=None, floor_strike=50.0, raw_data={}),
            DiscoveredMarket(ticker="M2", close_time="", cap_strike=None, floor_strike=100.0, raw_data={}),
        ]
        result = sort_markets_by_strike(markets)
        assert [m.ticker for m in result] == ["M1", "M2", "M3"]

    def test_markets_without_strikes_sort_last(self) -> None:
        """Test markets without valid strikes are placed at the end."""
        markets = [
            DiscoveredMarket(ticker="M2", close_time="", cap_strike=None, floor_strike=None, raw_data={}),
            DiscoveredMarket(ticker="M1", close_time="", cap_strike=None, floor_strike=50.0, raw_data={}),
        ]
        result = sort_markets_by_strike(markets)
        assert [m.ticker for m in result] == ["M1", "M2"]

    def test_empty_list(self) -> None:
        """Test handles empty list."""
        result = sort_markets_by_strike([])
        assert result == []

    def test_single_market(self) -> None:
        """Test handles single market."""
        market = DiscoveredMarket(ticker="M1", close_time="", cap_strike=None, floor_strike=50.0, raw_data={})
        result = sort_markets_by_strike([market])
        assert len(result) == 1
        assert result[0].ticker == "M1"
