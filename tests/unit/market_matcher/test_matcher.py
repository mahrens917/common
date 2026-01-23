"""Tests for market_matcher module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from common.market_matcher.matcher import (
    MarketMatcher,
    _build_match_from_pair,
    _effective_strike,
    _expiry_delta_hours,
    _filter_by_expiry_window,
    _parse_strike_from_outcome,
    _strikes_match_exact,
    _try_parse_float,
)
from common.market_matcher.types import MatchCandidate


class TestTryParseFloat:
    """Tests for _try_parse_float function."""

    def test_parses_valid_float(self) -> None:
        """Test parsing a valid float string."""
        assert _try_parse_float("123.45") == 123.45

    def test_returns_none_for_invalid(self) -> None:
        """Test returns None for invalid string."""
        assert _try_parse_float("invalid") is None


class TestParseStrikeFromOutcome:
    """Tests for _parse_strike_from_outcome function."""

    def test_parses_above_pattern(self) -> None:
        """Test parsing 'above' pattern."""
        assert _parse_strike_from_outcome("above $100") == 100.0

    def test_parses_below_pattern(self) -> None:
        """Test parsing 'below' pattern."""
        assert _parse_strike_from_outcome("below $50") == 50.0

    def test_parses_greater_than(self) -> None:
        """Test parsing 'greater than' pattern."""
        assert _parse_strike_from_outcome("greater than 200") == 200.0

    def test_parses_or_more(self) -> None:
        """Test parsing 'or more' pattern."""
        assert _parse_strike_from_outcome("$150 or more") == 150.0

    def test_parses_plain_number(self) -> None:
        """Test parsing plain number."""
        assert _parse_strike_from_outcome("100") == 100.0

    def test_returns_none_for_no_match(self) -> None:
        """Test returns None when no pattern matches."""
        assert _parse_strike_from_outcome("no numbers here") is None

    def test_handles_commas(self) -> None:
        """Test handles comma-separated numbers."""
        assert _parse_strike_from_outcome("above $1,000") == 1000.0


class TestEffectiveStrike:
    """Tests for _effective_strike function."""

    def test_returns_average_when_both_present(self) -> None:
        """Test returns average of floor and cap."""
        assert _effective_strike(100.0, 200.0) == 150.0

    def test_returns_floor_when_cap_is_inf(self) -> None:
        """Test returns floor when cap is infinity."""
        assert _effective_strike(100.0, float("inf")) == 100.0

    def test_returns_cap_when_floor_is_zero(self) -> None:
        """Test returns cap when floor is zero."""
        assert _effective_strike(0.0, 200.0) == 200.0

    def test_returns_cap_when_floor_is_neg_inf(self) -> None:
        """Test returns cap when floor is negative infinity."""
        assert _effective_strike(float("-inf"), 200.0) == 200.0

    def test_returns_floor_when_only_floor(self) -> None:
        """Test returns floor when only floor is set."""
        assert _effective_strike(100.0, None) == 100.0

    def test_returns_cap_when_only_cap(self) -> None:
        """Test returns cap when only cap is set."""
        assert _effective_strike(None, 200.0) == 200.0

    def test_returns_none_when_neither(self) -> None:
        """Test returns None when neither is set."""
        assert _effective_strike(None, None) is None


class TestStrikesMatchExact:
    """Tests for _strikes_match_exact function."""

    def test_both_none_returns_false_true(self) -> None:
        """Test returns (False, True) when neither has strikes."""
        has_numeric, matches = _strikes_match_exact(None, None, None, None)
        assert has_numeric is False
        assert matches is True

    def test_only_kalshi_has_strike_returns_true_false(self) -> None:
        """Test returns (True, False) when only Kalshi has strike."""
        has_numeric, matches = _strikes_match_exact(100.0, None, None, None)
        assert has_numeric is True
        assert matches is False

    def test_only_poly_has_strike_returns_true_false(self) -> None:
        """Test returns (True, False) when only Poly has strike."""
        has_numeric, matches = _strikes_match_exact(None, None, 100.0, None)
        assert has_numeric is True
        assert matches is False

    def test_equal_strikes_returns_true_true(self) -> None:
        """Test returns (True, True) when strikes match."""
        has_numeric, matches = _strikes_match_exact(100.0, None, 100.0, None)
        assert has_numeric is True
        assert matches is True

    def test_unequal_strikes_returns_true_false(self) -> None:
        """Test returns (True, False) when strikes don't match."""
        has_numeric, matches = _strikes_match_exact(100.0, None, 200.0, None)
        assert has_numeric is True
        assert matches is False


class TestExpiryDeltaHours:
    """Tests for _expiry_delta_hours function."""

    def test_returns_zero_for_same_time(self) -> None:
        """Test returns 0 for identical times."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert _expiry_delta_hours(dt, dt) == 0.0

    def test_returns_positive_for_different_times(self) -> None:
        """Test returns positive value for different times."""
        dt1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        dt2 = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)
        assert _expiry_delta_hours(dt1, dt2) == 2.0

    def test_returns_absolute_difference(self) -> None:
        """Test returns absolute difference regardless of order."""
        dt1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        dt2 = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)
        assert _expiry_delta_hours(dt1, dt2) == _expiry_delta_hours(dt2, dt1)


class TestFilterByExpiryWindow:
    """Tests for _filter_by_expiry_window function."""

    def test_filters_within_window(self) -> None:
        """Test filters candidates within window."""
        ref_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        candidates = [
            MatchCandidate("M1", "T1", "D1", ref_time + timedelta(hours=1), None, None, "k"),
            MatchCandidate("M2", "T2", "D2", ref_time + timedelta(hours=25), None, None, "k"),
        ]
        result = _filter_by_expiry_window(candidates, ref_time, 24.0)
        assert len(result) == 1
        assert result[0].market_id == "M1"

    def test_returns_empty_for_all_outside_window(self) -> None:
        """Test returns empty list when all candidates outside window."""
        ref_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        candidates = [
            MatchCandidate("M1", "T1", "D1", ref_time + timedelta(hours=25), None, None, "k"),
        ]
        result = _filter_by_expiry_window(candidates, ref_time, 24.0)
        assert len(result) == 0


class TestBuildMatchFromPair:
    """Tests for _build_match_from_pair function."""

    def test_returns_match_within_window(self) -> None:
        """Test returns match when within expiry window."""
        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        kalshi = MatchCandidate("K1", "T", "D", expiry, 100.0, None, "kalshi")
        poly = MatchCandidate("P1", "T", "D", expiry + timedelta(hours=1), 100.0, None, "poly")

        match = _build_match_from_pair(kalshi, poly, 0.85, 24.0)

        assert match is not None
        assert match.kalshi_market_id == "K1"
        assert match.poly_market_id == "P1"
        assert match.title_similarity == 0.85

    def test_returns_none_outside_window(self) -> None:
        """Test returns None when outside expiry window."""
        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        kalshi = MatchCandidate("K1", "T", "D", expiry, None, None, "kalshi")
        poly = MatchCandidate("P1", "T", "D", expiry + timedelta(hours=25), None, None, "poly")

        match = _build_match_from_pair(kalshi, poly, 0.85, 24.0)

        assert match is None


class TestMarketMatcher:
    """Tests for MarketMatcher class."""

    def test_init_sets_defaults(self) -> None:
        """Test initialization sets default values."""
        embedding_service = MagicMock()
        matcher = MarketMatcher(embedding_service)
        assert matcher._similarity_threshold == 0.75
        assert matcher._expiry_window_hours == 24.0

    def test_init_accepts_custom_values(self) -> None:
        """Test initialization accepts custom values."""
        embedding_service = MagicMock()
        matcher = MarketMatcher(embedding_service, similarity_threshold=0.9, expiry_window_hours=12.0)
        assert matcher._similarity_threshold == 0.9
        assert matcher._expiry_window_hours == 12.0

    @pytest.mark.asyncio
    async def test_match_returns_empty_for_empty_kalshi(self) -> None:
        """Test match returns empty list for empty Kalshi markets."""
        embedding_service = MagicMock()
        matcher = MarketMatcher(embedding_service)

        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        poly = [MatchCandidate("P1", "T", "D", expiry, None, None, "poly")]

        result = await matcher.match([], poly)
        assert result == []

    @pytest.mark.asyncio
    async def test_match_returns_empty_for_empty_poly(self) -> None:
        """Test match returns empty list for empty Poly markets."""
        embedding_service = MagicMock()
        matcher = MarketMatcher(embedding_service)

        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        kalshi = [MatchCandidate("K1", "T", "D", expiry, None, None, "kalshi")]

        result = await matcher.match(kalshi, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_match_filters_by_similarity(self) -> None:
        """Test match filters by similarity threshold."""
        embedding_service = MagicMock()
        embedding_service.embed = AsyncMock(return_value=np.ones((1, 1), dtype=np.float32))
        embedding_service.compute_similarity_matrix.return_value = np.full((1, 1), 0.5, dtype=np.float32)

        matcher = MarketMatcher(embedding_service, similarity_threshold=0.75)

        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        kalshi = [MatchCandidate("K1", "Title", "Desc", expiry, None, None, "kalshi")]
        poly = [MatchCandidate("P1", "Title", "Desc", expiry, None, None, "poly")]

        result = await matcher.match(kalshi, poly)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_match_includes_above_threshold(self) -> None:
        """Test match includes matches above threshold."""
        embedding_service = MagicMock()
        embedding_service.embed = AsyncMock(return_value=np.ones((1, 1), dtype=np.float32))
        embedding_service.compute_similarity_matrix.return_value = np.full((1, 1), 0.85, dtype=np.float32)

        matcher = MarketMatcher(embedding_service, similarity_threshold=0.75)

        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        kalshi = [MatchCandidate("K1", "Title", "Desc", expiry, None, None, "kalshi")]
        poly = [MatchCandidate("P1", "Title", "Desc", expiry, None, None, "poly")]

        result = await matcher.match(kalshi, poly)
        assert len(result) == 1
        assert result[0].title_similarity == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_match_with_strike_filter_filters_non_matching(self) -> None:
        """Test match_with_strike_filter filters non-matching strikes."""
        embedding_service = MagicMock()
        embedding_service.embed = AsyncMock(return_value=np.ones((1, 1), dtype=np.float32))
        embedding_service.compute_similarity_matrix.return_value = np.full((1, 1), 0.85, dtype=np.float32)

        matcher = MarketMatcher(embedding_service)

        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        kalshi = [MatchCandidate("K1", "Title", "Desc", expiry, 100.0, None, "kalshi")]
        poly = [MatchCandidate("P1", "Title", "Desc", expiry, 200.0, None, "poly")]

        result = await matcher.match_with_strike_filter(kalshi, poly)
        assert len(result) == 0


class TestMarketMatcherAsync:
    """Tests for MarketMatcher async methods."""

    @pytest.mark.asyncio
    async def test_match_with_cache_returns_empty_for_empty_markets(self) -> None:
        """Test match_with_cache returns empty for empty markets."""
        embedding_service = MagicMock()
        matcher = MarketMatcher(embedding_service)
        redis = AsyncMock()

        result = await matcher.match_with_cache([], [], redis)
        assert result == []

    @pytest.mark.asyncio
    async def test_match_with_cache_and_strike_filter_delegates(self) -> None:
        """Test match_with_cache_and_strike_filter delegates to match_with_cache."""
        embedding_service = MagicMock()
        embedding_service.embed_with_cache = AsyncMock(return_value=np.ones((1, 1), dtype=np.float32))
        embedding_service.compute_similarity_matrix.return_value = np.full((1, 1), 0.85, dtype=np.float32)

        matcher = MarketMatcher(embedding_service)
        redis = AsyncMock()

        expiry = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        kalshi = [MatchCandidate("K1", "Title", "Desc", expiry, 100.0, None, "kalshi")]
        poly = [MatchCandidate("P1", "Title", "Desc", expiry, 100.0, None, "poly")]

        result = await matcher.match_with_cache_and_strike_filter(kalshi, poly, redis)
        # Should have a match since strikes match
        assert len(result) == 1
