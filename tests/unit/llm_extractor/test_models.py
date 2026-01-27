"""Tests for llm_extractor models module."""

import pytest

from common.llm_extractor.models import VALID_POLY_STRIKE_TYPES, MarketExtraction


class TestValidPolyStrikeTypes:
    """Tests for VALID_POLY_STRIKE_TYPES constant."""

    def test_contains_greater(self) -> None:
        """Test that 'greater' is a valid strike type."""
        assert "greater" in VALID_POLY_STRIKE_TYPES

    def test_contains_less(self) -> None:
        """Test that 'less' is a valid strike type."""
        assert "less" in VALID_POLY_STRIKE_TYPES

    def test_contains_between(self) -> None:
        """Test that 'between' is a valid strike type."""
        assert "between" in VALID_POLY_STRIKE_TYPES

    def test_is_frozenset(self) -> None:
        """Test that VALID_POLY_STRIKE_TYPES is immutable."""
        assert isinstance(VALID_POLY_STRIKE_TYPES, frozenset)

    def test_has_exactly_three_types(self) -> None:
        """Test that there are exactly 3 valid strike types."""
        assert len(VALID_POLY_STRIKE_TYPES) == 3


class TestMarketExtraction:
    """Tests for MarketExtraction dataclass."""

    def test_creates_with_required_fields(self) -> None:
        """Test creating extraction with only required fields."""
        extraction = MarketExtraction(
            market_id="m1",
            platform="poly",
            category="Crypto",
            underlying="BTC",
        )
        assert extraction.market_id == "m1"
        assert extraction.platform == "poly"
        assert extraction.category == "Crypto"
        assert extraction.underlying == "BTC"
        assert extraction.strike_type is None
        assert extraction.floor_strike is None
        assert extraction.cap_strike is None
        assert extraction.close_time is None

    def test_creates_with_all_fields(self) -> None:
        """Test creating extraction with all fields."""
        extraction = MarketExtraction(
            market_id="m1",
            platform="kalshi",
            category="Crypto",
            underlying="ETH",
            strike_type="between",
            floor_strike=3500.0,
            cap_strike=3600.0,
            close_time="2026-01-27T20:00:00+00:00",
        )
        assert extraction.market_id == "m1"
        assert extraction.platform == "kalshi"
        assert extraction.category == "Crypto"
        assert extraction.underlying == "ETH"
        assert extraction.strike_type == "between"
        assert extraction.floor_strike == 3500.0
        assert extraction.cap_strike == 3600.0
        assert extraction.close_time == "2026-01-27T20:00:00+00:00"

    def test_is_frozen(self) -> None:
        """Test that MarketExtraction is immutable."""
        extraction = MarketExtraction(
            market_id="m1",
            platform="poly",
            category="Crypto",
            underlying="BTC",
        )
        with pytest.raises(AttributeError):
            extraction.category = "Sports"  # type: ignore[misc]

    def test_is_hashable(self) -> None:
        """Test that MarketExtraction is hashable (frozen dataclass)."""
        extraction = MarketExtraction(
            market_id="X",
            platform="poly",
            category="Crypto",
            underlying="BTC",
        )
        assert hash(extraction) is not None

    def test_negative_strikes_allowed(self) -> None:
        """Test that negative strike values are allowed."""
        extraction = MarketExtraction(
            market_id="m1",
            platform="poly",
            category="Economics",
            underlying="FED",
            strike_type="less",
            floor_strike=-0.5,
            cap_strike=0.0,
        )
        assert extraction.floor_strike == -0.5
        assert extraction.cap_strike == 0.0
