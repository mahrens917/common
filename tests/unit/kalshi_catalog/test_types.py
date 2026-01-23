"""Tests for kalshi_catalog types."""

import pytest

from common.kalshi_catalog.types import (
    CatalogDiscoveryError,
    DiscoveredEvent,
    DiscoveredMarket,
)


class TestDiscoveredMarket:
    """Tests for DiscoveredMarket dataclass."""

    def test_creates_with_all_fields(self) -> None:
        """Test creating DiscoveredMarket with all fields."""
        raw = {"ticker": "TEST-123", "close_time": "2024-01-01T00:00:00Z"}
        market = DiscoveredMarket(
            ticker="TEST-123",
            close_time="2024-01-01T00:00:00Z",
            subtitle="Test subtitle",
            cap_strike=100.0,
            floor_strike=50.0,
            raw_data=raw,
        )
        assert market.ticker == "TEST-123"
        assert market.close_time == "2024-01-01T00:00:00Z"
        assert market.subtitle == "Test subtitle"
        assert market.cap_strike == 100.0
        assert market.floor_strike == 50.0
        assert market.raw_data == raw

    def test_creates_with_none_strikes(self) -> None:
        """Test creating DiscoveredMarket with None strikes."""
        market = DiscoveredMarket(
            ticker="TEST",
            close_time="2024-01-01T00:00:00Z",
            subtitle="",
            cap_strike=None,
            floor_strike=100.0,
            raw_data={},
        )
        assert market.cap_strike is None
        assert market.floor_strike == 100.0


class TestDiscoveredEvent:
    """Tests for DiscoveredEvent dataclass."""

    def test_creates_with_all_fields(self) -> None:
        """Test creating DiscoveredEvent with all fields."""
        market = DiscoveredMarket(
            ticker="M1",
            close_time="2024-01-01T00:00:00Z",
            subtitle="",
            cap_strike=100.0,
            floor_strike=None,
            raw_data={},
        )
        event = DiscoveredEvent(
            event_ticker="EVENT-1",
            title="Test Event",
            category="Crypto",
            mutually_exclusive=True,
            markets=[market],
        )
        assert event.event_ticker == "EVENT-1"
        assert event.title == "Test Event"
        assert event.category == "Crypto"
        assert event.mutually_exclusive is True
        assert len(event.markets) == 1
        assert event.markets[0].ticker == "M1"


class TestExceptions:
    """Tests for exception classes."""

    def test_catalog_discovery_error_is_runtime_error(self) -> None:
        """Test CatalogDiscoveryError inherits from RuntimeError."""
        error = CatalogDiscoveryError("test error")
        assert isinstance(error, RuntimeError)
        assert str(error) == "test error"

    def test_catalog_discovery_error_can_be_raised(self) -> None:
        """Test CatalogDiscoveryError can be raised and caught."""
        with pytest.raises(CatalogDiscoveryError, match="discovery failed"):
            raise CatalogDiscoveryError("discovery failed")
