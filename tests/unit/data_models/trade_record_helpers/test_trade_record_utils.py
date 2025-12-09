"""Unit tests for trade record utility functions."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.common.data_models.trade_record_helpers.trade_record_utils import (
    ALLOWED_SHORT_TRADE_REASONS,
    get_trade_close_date,
    is_trade_reason_valid,
)


class TestIsTradeReasonValid:
    """Tests for is_trade_reason_valid function."""

    def test_accepts_long_reason(self) -> None:
        """Test that reasons with 10+ characters are valid."""
        assert is_trade_reason_valid("this is a long enough reason") is True
        assert is_trade_reason_valid("exactly 10") is True  # Exactly 10 characters
        assert is_trade_reason_valid("1234567890") is True  # Exactly 10 characters

    def test_rejects_short_reason_not_in_allowed_list(self) -> None:
        """Test that short reasons not in ALLOWED_SHORT_TRADE_REASONS are invalid."""
        assert is_trade_reason_valid("short") is False
        assert is_trade_reason_valid("abc") is False
        assert is_trade_reason_valid("123456789") is False  # 9 characters

    def test_accepts_storm_reason(self) -> None:
        """Test that 'storm' is accepted as a valid short reason."""
        assert is_trade_reason_valid("storm") is True
        assert is_trade_reason_valid("STORM") is True
        assert is_trade_reason_valid("Storm") is True
        assert is_trade_reason_valid("  storm  ") is True  # With whitespace

    def test_accepts_rebalance_reason(self) -> None:
        """Test that 'rebalance' is accepted as a valid short reason."""
        assert is_trade_reason_valid("rebalance") is True
        assert is_trade_reason_valid("REBALANCE") is True
        assert is_trade_reason_valid("Rebalance") is True
        assert is_trade_reason_valid("  rebalance  ") is True  # With whitespace

    def test_rejects_empty_string(self) -> None:
        """Test that empty strings are invalid."""
        assert is_trade_reason_valid("") is False
        assert is_trade_reason_valid("   ") is False  # Only whitespace
        assert is_trade_reason_valid("\t\n") is False  # Only whitespace chars

    def test_normalizes_case_and_whitespace(self) -> None:
        """Test that reasons are normalized before validation."""
        assert is_trade_reason_valid("  STORM  ") is True
        assert is_trade_reason_valid("\tstorm\n") is True
        assert is_trade_reason_valid("  this is a long reason  ") is True

    def test_boundary_cases_for_length(self) -> None:
        """Test boundary cases around 10 character threshold."""
        assert is_trade_reason_valid("123456789") is False  # 9 chars - invalid
        assert is_trade_reason_valid("1234567890") is True  # 10 chars - valid
        assert is_trade_reason_valid("12345678901") is True  # 11 chars - valid

    def test_allowed_short_reasons_constant(self) -> None:
        """Test that ALLOWED_SHORT_TRADE_REASONS contains expected values."""
        assert "storm" in ALLOWED_SHORT_TRADE_REASONS
        assert "rebalance" in ALLOWED_SHORT_TRADE_REASONS
        assert len(ALLOWED_SHORT_TRADE_REASONS) == 2


class TestGetTradeCloseDate:
    """Tests for get_trade_close_date function."""

    def test_returns_settlement_date_when_available(self) -> None:
        """Test that settlement_time.date() is returned when settlement_time is set."""
        trade = MagicMock()
        trade.settlement_time = datetime(2025, 1, 15, 14, 30, tzinfo=timezone.utc)
        trade.trade_timestamp = datetime(2025, 1, 10, 10, 0, tzinfo=timezone.utc)

        result = get_trade_close_date(trade)

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_returns_trade_date_when_settlement_is_none(self) -> None:
        """Test that trade_timestamp.date() is returned when settlement_time is None."""
        trade = MagicMock()
        trade.settlement_time = None
        trade.trade_timestamp = datetime(2025, 1, 10, 10, 0, tzinfo=timezone.utc)

        result = get_trade_close_date(trade)

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 10

    def test_prefers_settlement_over_trade_timestamp(self) -> None:
        """Test that settlement_time takes precedence over trade_timestamp."""
        trade = MagicMock()
        trade.settlement_time = datetime(2025, 1, 20, 16, 45, tzinfo=timezone.utc)
        trade.trade_timestamp = datetime(2025, 1, 15, 12, 30, tzinfo=timezone.utc)

        result = get_trade_close_date(trade)

        # Should use settlement_time, not trade_timestamp
        assert result.day == 20
        assert result != trade.trade_timestamp.date()

    def test_handles_different_timezones(self) -> None:
        """Test that datetime timezone information doesn't affect date extraction."""
        trade = MagicMock()
        trade.settlement_time = datetime(2025, 1, 15, 23, 59, tzinfo=timezone.utc)
        trade.trade_timestamp = datetime(2025, 1, 10, 0, 1, tzinfo=timezone.utc)

        result = get_trade_close_date(trade)

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_handles_edge_case_midnight_transition(self) -> None:
        """Test date extraction at midnight boundaries."""
        trade = MagicMock()
        trade.settlement_time = None
        trade.trade_timestamp = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = get_trade_close_date(trade)

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

    def test_handles_end_of_month(self) -> None:
        """Test date extraction at end of month."""
        trade = MagicMock()
        trade.settlement_time = datetime(2025, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        trade.trade_timestamp = datetime(2025, 1, 28, 12, 0, tzinfo=timezone.utc)

        result = get_trade_close_date(trade)

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 31
