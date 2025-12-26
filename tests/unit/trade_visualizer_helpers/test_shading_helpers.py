"""Tests for trade_visualizer_helpers.shading_helpers module."""

from unittest.mock import MagicMock

import pytest

from common.data_models.trade_record import TradeRecord, TradeSide
from common.trade_visualizer_helpers.shading_helpers import (
    apply_single_shading,
    find_next_strike,
    get_strike_bounds,
    get_trade_color,
)

# Test constants for data_guard compliance
TEST_MIN_STRIKE_65 = 65.0
TEST_MIN_STRIKE_70 = 70.0
TEST_MAX_STRIKE_74 = 74.0
TEST_MAX_STRIKE_85 = 85.0


class TestFindNextStrike:
    """Tests for find_next_strike function."""

    def test_finds_next_strike(self) -> None:
        """Test finding next strike above trade price."""
        strikes = [70.0, 72.0, 74.0, 76.0]

        result = find_next_strike(72.5, strikes)

        assert result == 74.0

    def test_finds_first_strike(self) -> None:
        """Test finding first strike when price is below all."""
        strikes = [70.0, 72.0, 74.0]

        result = find_next_strike(68.0, strikes)

        assert result == 70.0

    def test_returns_price_plus_one_when_no_higher(self) -> None:
        """Test returns price + 1 when no higher strike exists."""
        strikes = [70.0, 72.0, 74.0]

        result = find_next_strike(75.0, strikes)

        assert result == 76.0

    def test_exact_match_returns_next(self) -> None:
        """Test exact match returns next strike."""
        strikes = [70.0, 72.0, 74.0]

        result = find_next_strike(72.0, strikes)

        assert result == 74.0

    def test_unsorted_strikes_are_sorted(self) -> None:
        """Test unsorted strikes are sorted before search."""
        strikes = [74.0, 70.0, 72.0]

        result = find_next_strike(71.0, strikes)

        assert result == 72.0


class TestGetTradeColor:
    """Tests for get_trade_color function."""

    def test_buy_trade_returns_buy_color(self) -> None:
        """Test buy trade returns buy color."""
        trade = MagicMock(spec=TradeRecord)
        trade.trade_side = TradeSide.YES

        result = get_trade_color(trade, "#00FF00", "#FF0000")

        assert result == "#00FF00"

    def test_sell_trade_returns_sell_color(self) -> None:
        """Test sell trade returns sell color."""
        trade = MagicMock(spec=TradeRecord)
        trade.trade_side = TradeSide.NO

        result = get_trade_color(trade, "#00FF00", "#FF0000")

        assert result == "#FF0000"


class TestGetStrikeBounds:
    """Tests for get_strike_bounds function."""

    def test_uses_state_strikes_when_present(self) -> None:
        """Test uses state strike values when both present."""
        state = MagicMock()
        state.min_strike_price_cents = TEST_MIN_STRIKE_65
        state.max_strike_price_cents = TEST_MAX_STRIKE_85
        strikes = [TEST_MIN_STRIKE_70, 72.0, TEST_MAX_STRIKE_74]

        y_min, y_max = get_strike_bounds(state, strikes)

        assert y_min == TEST_MIN_STRIKE_65
        assert y_max == TEST_MAX_STRIKE_85

    def test_uses_strikes_when_state_min_none(self) -> None:
        """Test uses strikes when state min is None."""
        state = MagicMock()
        state.min_strike_price_cents = None
        state.max_strike_price_cents = TEST_MAX_STRIKE_85
        strikes = [TEST_MIN_STRIKE_70, 72.0, TEST_MAX_STRIKE_74]

        y_min, y_max = get_strike_bounds(state, strikes)

        assert y_min == TEST_MIN_STRIKE_70
        assert y_max == TEST_MAX_STRIKE_74

    def test_uses_strikes_when_state_max_none(self) -> None:
        """Test uses strikes when state max is None."""
        state = MagicMock()
        state.min_strike_price_cents = TEST_MIN_STRIKE_65
        state.max_strike_price_cents = None
        strikes = [TEST_MIN_STRIKE_70, 72.0, TEST_MAX_STRIKE_74]

        y_min, y_max = get_strike_bounds(state, strikes)

        assert y_min == TEST_MIN_STRIKE_70
        assert y_max == TEST_MAX_STRIKE_74


class TestApplySingleShading:
    """Tests for apply_single_shading function."""

    def test_applies_shading_to_axes(self) -> None:
        """Test applies horizontal span to axes."""
        mock_ax = MagicMock()

        apply_single_shading(mock_ax, 1, 70.0, 75.0, "#90EE90", 0.3)

        mock_ax.axhspan.assert_called_once_with(70.0, 75.0, alpha=0.3, color="#90EE90", zorder=5, label="Trade 1")

    def test_increments_label_index(self) -> None:
        """Test label includes index number."""
        mock_ax = MagicMock()

        apply_single_shading(mock_ax, 5, 80.0, 85.0, "#FFB6C1", 0.5)

        mock_ax.axhspan.assert_called_once()
        call_kwargs = mock_ax.axhspan.call_args[1]
        assert call_kwargs["label"] == "Trade 5"
