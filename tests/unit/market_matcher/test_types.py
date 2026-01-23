"""Tests for market_matcher types."""

from datetime import datetime, timezone

from common.market_matcher.types import MarketMatch, MatchCandidate


class TestMatchCandidate:
    """Tests for MatchCandidate dataclass."""

    def test_creates_with_all_fields(self) -> None:
        """Test creating MatchCandidate with all fields."""
        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        candidate = MatchCandidate(
            market_id="TEST-123",
            title="Test Title",
            description="Test description",
            expiry=expiry,
            floor_strike=100.0,
            cap_strike=200.0,
            source="kalshi",
        )
        assert candidate.market_id == "TEST-123"
        assert candidate.title == "Test Title"
        assert candidate.description == "Test description"
        assert candidate.expiry == expiry
        assert candidate.floor_strike == 100.0
        assert candidate.cap_strike == 200.0
        assert candidate.source == "kalshi"

    def test_creates_with_none_strikes(self) -> None:
        """Test creating MatchCandidate with None strikes."""
        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        candidate = MatchCandidate(
            market_id="TEST",
            title="Title",
            description="Desc",
            expiry=expiry,
            floor_strike=None,
            cap_strike=None,
            source="poly",
        )
        assert candidate.floor_strike is None
        assert candidate.cap_strike is None

    def test_is_frozen(self) -> None:
        """Test that MatchCandidate is immutable."""
        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        candidate = MatchCandidate(
            market_id="TEST",
            title="Title",
            description="Desc",
            expiry=expiry,
            floor_strike=None,
            cap_strike=None,
            source="kalshi",
        )
        # Should be hashable since it's frozen
        assert hash(candidate) is not None


class TestMarketMatch:
    """Tests for MarketMatch dataclass."""

    def test_creates_with_all_fields(self) -> None:
        """Test creating MarketMatch with all fields."""
        match = MarketMatch(
            kalshi_market_id="KALSHI-123",
            poly_market_id="POLY-456",
            title_similarity=0.85,
            expiry_delta_hours=2.5,
            strike_match=True,
        )
        assert match.kalshi_market_id == "KALSHI-123"
        assert match.poly_market_id == "POLY-456"
        assert match.title_similarity == 0.85
        assert match.expiry_delta_hours == 2.5
        assert match.strike_match is True

    def test_strike_match_false(self) -> None:
        """Test creating MarketMatch with non-matching strikes."""
        match = MarketMatch(
            kalshi_market_id="K1",
            poly_market_id="P1",
            title_similarity=0.9,
            expiry_delta_hours=1.0,
            strike_match=False,
        )
        assert match.strike_match is False

    def test_is_frozen(self) -> None:
        """Test that MarketMatch is immutable."""
        match = MarketMatch(
            kalshi_market_id="K1",
            poly_market_id="P1",
            title_similarity=0.9,
            expiry_delta_hours=1.0,
            strike_match=True,
        )
        # Should be hashable since it's frozen
        assert hash(match) is not None
