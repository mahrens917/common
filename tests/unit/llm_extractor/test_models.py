"""Tests for llm_extractor models."""

import pytest

from common.llm_extractor.models import KALSHI_CATEGORIES, MarketExtraction


class TestMarketExtraction:
    """Tests for MarketExtraction dataclass."""

    def test_creates_with_required_fields(self) -> None:
        """Test creating MarketExtraction with required fields."""
        extraction = MarketExtraction(
            market_id="TEST-123",
            platform="poly",
            category="Crypto",
            underlying="BTC",
            subject="BTC",
            entity="BTC price",
            scope="above 100000",
        )
        assert extraction.market_id == "TEST-123"
        assert extraction.platform == "poly"
        assert extraction.category == "Crypto"
        assert extraction.underlying == "BTC"
        assert extraction.subject == "BTC"
        assert extraction.entity == "BTC price"
        assert extraction.scope == "above 100000"

    def test_optional_fields_are_none_by_default(self) -> None:
        """Test that optional fields default to None/False/empty."""
        extraction = MarketExtraction(
            market_id="X",
            platform="kalshi",
            category="Finance",
            underlying="SPY",
            subject="SPY",
            entity="SPY price",
            scope="above 500",
        )
        assert extraction.floor_strike is None
        assert extraction.cap_strike is None
        assert extraction.parent_entity is None
        assert extraction.parent_scope is None
        assert extraction.is_conjunction is False
        assert extraction.conjunction_scopes == ()
        assert extraction.is_union is False
        assert extraction.union_scopes == ()

    def test_creates_with_all_fields(self) -> None:
        """Test creating MarketExtraction with all fields populated."""
        extraction = MarketExtraction(
            market_id="KXETHD-26JAN",
            platform="kalshi",
            category="Crypto",
            underlying="ETH",
            subject="ETH",
            entity="ETH price",
            scope="between 3500 and 3600",
            floor_strike=3500.0,
            cap_strike=3600.0,
            parent_entity="ETH daily close",
            parent_scope="above 3000",
            is_conjunction=True,
            conjunction_scopes=("ETH above 3500", "BTC above 100000"),
            is_union=False,
            union_scopes=(),
        )
        assert extraction.floor_strike == 3500.0
        assert extraction.cap_strike == 3600.0
        assert extraction.parent_entity == "ETH daily close"
        assert extraction.parent_scope == "above 3000"
        assert extraction.is_conjunction is True
        assert extraction.conjunction_scopes == ("ETH above 3500", "BTC above 100000")

    def test_is_frozen(self) -> None:
        """Test that MarketExtraction is immutable."""
        extraction = MarketExtraction(
            market_id="X",
            platform="poly",
            category="Crypto",
            underlying="BTC",
            subject="BTC",
            entity="BTC price",
            scope="above 100000",
        )
        with pytest.raises(AttributeError):
            extraction.market_id = "Y"  # type: ignore[misc]

    def test_is_hashable(self) -> None:
        """Test that MarketExtraction is hashable (frozen dataclass)."""
        extraction = MarketExtraction(
            market_id="X",
            platform="poly",
            category="Crypto",
            underlying="BTC",
            subject="BTC",
            entity="BTC price",
            scope="above 100000",
        )
        assert hash(extraction) is not None


class TestKalshiCategories:
    """Tests for KALSHI_CATEGORIES constant."""

    def test_is_tuple(self) -> None:
        """Test that KALSHI_CATEGORIES is a tuple."""
        assert isinstance(KALSHI_CATEGORIES, tuple)

    def test_contains_expected_categories(self) -> None:
        """Test that key categories are present."""
        assert "Crypto" in KALSHI_CATEGORIES
        assert "Politics" in KALSHI_CATEGORIES
        assert "Sports" in KALSHI_CATEGORIES
        assert "Finance" in KALSHI_CATEGORIES

    def test_has_ten_categories(self) -> None:
        """Test that there are exactly 10 categories."""
        assert len(KALSHI_CATEGORIES) == 10
