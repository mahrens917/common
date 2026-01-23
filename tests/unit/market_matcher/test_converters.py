"""Tests for market_matcher converters."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from common.market_matcher.converters import (
    _extract_poly_strike_from_tokens,
    _extract_strike_from_outcome,
    _parse_iso_datetime,
    _try_parse_float,
    kalshi_market_to_candidate,
    poly_market_to_candidate,
)


class TestTryParseFloat:
    """Tests for _try_parse_float function."""

    def test_parses_valid_float(self) -> None:
        """Test parsing a valid float string."""
        assert _try_parse_float("123.45") == 123.45

    def test_parses_integer(self) -> None:
        """Test parsing an integer string."""
        assert _try_parse_float("100") == 100.0

    def test_returns_none_for_invalid(self) -> None:
        """Test returns None for invalid string."""
        assert _try_parse_float("not-a-number") is None

    def test_returns_none_for_empty(self) -> None:
        """Test returns None for empty string."""
        assert _try_parse_float("") is None


class TestParseIsoDatetime:
    """Tests for _parse_iso_datetime function."""

    def test_parses_with_z_suffix(self) -> None:
        """Test parsing ISO datetime with Z suffix."""
        result = _parse_iso_datetime("2024-01-01T12:00:00Z")
        assert result == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_parses_with_offset(self) -> None:
        """Test parsing ISO datetime with offset."""
        result = _parse_iso_datetime("2024-01-01T12:00:00+00:00")
        assert result == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestExtractStrikeFromOutcome:
    """Tests for _extract_strike_from_outcome function."""

    def test_extracts_above_pattern(self) -> None:
        """Test extracting strike from 'above' pattern."""
        patterns = [r"(?:above|over)\s*\$?([\d,]+\.?\d*)"]
        assert _extract_strike_from_outcome("above $100", patterns) == 100.0

    def test_extracts_with_commas(self) -> None:
        """Test extracting strike with comma separators."""
        patterns = [r"(?:above|over)\s*\$?([\d,]+\.?\d*)"]
        assert _extract_strike_from_outcome("above $1,000", patterns) == 1000.0

    def test_returns_none_for_no_match(self) -> None:
        """Test returns None when no pattern matches."""
        patterns = [r"(?:above|over)\s*\$?([\d,]+\.?\d*)"]
        assert _extract_strike_from_outcome("some text", patterns) is None


class TestExtractPolyStrikeFromTokens:
    """Tests for _extract_poly_strike_from_tokens function."""

    def test_returns_none_for_empty_tokens(self) -> None:
        """Test returns (None, None) for empty tokens list."""
        assert _extract_poly_strike_from_tokens([]) == (None, None)

    def test_extracts_floor_from_above_pattern(self) -> None:
        """Test extracting floor strike from above pattern."""
        token = MagicMock()
        token.outcome = "above $100"
        floor, cap = _extract_poly_strike_from_tokens([token])
        assert floor == 100.0
        assert cap is None

    def test_extracts_cap_from_below_pattern(self) -> None:
        """Test extracting cap strike from below pattern."""
        token = MagicMock()
        token.outcome = "below $50"
        floor, cap = _extract_poly_strike_from_tokens([token])
        assert floor is None
        assert cap == 50.0

    def test_extracts_both_strikes(self) -> None:
        """Test extracting both floor and cap from multiple tokens."""
        token_above = MagicMock()
        token_above.outcome = "above $100"
        token_below = MagicMock()
        token_below.outcome = "below $200"
        floor, cap = _extract_poly_strike_from_tokens([token_above, token_below])
        assert floor == 100.0
        assert cap == 200.0

    def test_handles_non_string_outcome(self) -> None:
        """Test handles token without string outcome attribute."""
        token = MagicMock()
        token.outcome = 12345  # Not a string
        floor, cap = _extract_poly_strike_from_tokens([token])
        assert floor is None
        assert cap is None

    def test_handles_token_without_outcome_attr(self) -> None:
        """Test handles token that uses str representation."""
        token = "above $50"
        floor, cap = _extract_poly_strike_from_tokens([token])
        assert floor == 50.0


class TestKalshiMarketToCandidate:
    """Tests for kalshi_market_to_candidate function."""

    def test_converts_kalshi_market(self) -> None:
        """Test converting Kalshi market to candidate."""
        market = MagicMock()
        market.ticker = "KALSHI-123"
        market.close_time = "2024-01-01T12:00:00Z"
        market.subtitle = "Test subtitle"
        market.floor_strike = 100.0
        market.cap_strike = 200.0

        candidate = kalshi_market_to_candidate(market, "Test Event")

        assert candidate.market_id == "KALSHI-123"
        assert candidate.title == "Test Event"
        assert candidate.description == "Test subtitle"
        assert candidate.floor_strike == 100.0
        assert candidate.cap_strike == 200.0
        assert candidate.source == "kalshi"


class TestPolyMarketToCandidate:
    """Tests for poly_market_to_candidate function."""

    def test_converts_poly_market(self) -> None:
        """Test converting Poly market to candidate."""
        market = MagicMock()
        market.condition_id = "POLY-456"
        market.title = "Poly Title"
        market.description = "Poly description"
        market.end_date = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        market.tokens = []

        candidate = poly_market_to_candidate(market)

        assert candidate.market_id == "POLY-456"
        assert candidate.title == "Poly Title"
        assert candidate.description == "Poly description"
        assert candidate.source == "poly"

    def test_adds_utc_to_naive_datetime(self) -> None:
        """Test adds UTC timezone to naive datetime."""
        market = MagicMock()
        market.condition_id = "POLY-789"
        market.title = "Title"
        market.description = "Desc"
        market.end_date = datetime(2024, 1, 1, 12, 0)  # Naive datetime
        market.tokens = []

        candidate = poly_market_to_candidate(market)

        assert candidate.expiry.tzinfo == timezone.utc

    def test_extracts_strikes_from_tokens(self) -> None:
        """Test extracting strikes from token outcomes."""
        market = MagicMock()
        market.condition_id = "POLY-999"
        market.title = "Title"
        market.description = "Desc"
        market.end_date = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        token = MagicMock()
        token.outcome = "above $100"
        market.tokens = [token]

        candidate = poly_market_to_candidate(market)

        assert candidate.floor_strike == 100.0
