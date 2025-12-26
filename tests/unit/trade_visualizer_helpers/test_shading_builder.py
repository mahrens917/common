"""Tests for trade_visualizer_helpers.shading_builder module."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from common.data_models.trade_record import TradeRecord, TradeSide
from common.trade_visualizer_helpers.shading_builder import (
    ShadingBuilder,
    TradeShading,
)


class TestTradeShading:
    """Tests for TradeShading dataclass."""

    def test_init(self) -> None:
        """Test TradeShading initialization."""
        start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

        shading = TradeShading(
            start_time=start,
            end_time=end,
            y_min=70.0,
            y_max=75.0,
            color="#90EE90",
            alpha=0.3,
            label="Test shading",
        )

        assert shading.start_time == start
        assert shading.end_time == end
        assert shading.y_min == 70.0
        assert shading.y_max == 75.0
        assert shading.color == "#90EE90"
        assert shading.alpha == 0.3
        assert shading.label == "Test shading"


class TestShadingBuilderIsNoLiquidityState:
    """Tests for ShadingBuilder.is_no_liquidity_state method."""

    def test_no_liquidity_both_none(self) -> None:
        """Test no liquidity when both bid and ask are None."""
        state = MagicMock()
        state.yes_bid = None
        state.yes_ask = None

        result = ShadingBuilder.is_no_liquidity_state(state)

        assert result is True

    def test_no_liquidity_bid_zero_ask_100(self) -> None:
        """Test no liquidity when bid is 0 and ask is 100."""
        state = MagicMock()
        state.yes_bid = 0
        state.yes_ask = 100

        result = ShadingBuilder.is_no_liquidity_state(state)

        assert result is True

    def test_no_liquidity_bid_none_ask_100(self) -> None:
        """Test no liquidity when bid is None and ask is 100."""
        state = MagicMock()
        state.yes_bid = None
        state.yes_ask = 100

        result = ShadingBuilder.is_no_liquidity_state(state)

        assert result is True

    def test_has_liquidity_normal_spread(self) -> None:
        """Test has liquidity with normal spread."""
        state = MagicMock()
        state.yes_bid = 45
        state.yes_ask = 55

        result = ShadingBuilder.is_no_liquidity_state(state)

        assert result is False

    def test_has_liquidity_bid_present(self) -> None:
        """Test has liquidity when bid is present."""
        state = MagicMock()
        state.yes_bid = 30
        state.yes_ask = 100

        result = ShadingBuilder.is_no_liquidity_state(state)

        assert result is False


class TestShadingBuilderCreateExecutedTradeShading:
    """Tests for ShadingBuilder.create_executed_trade_shading method."""

    def test_creates_buy_shading(self) -> None:
        """Test creating shading for buy trade."""
        builder = ShadingBuilder()
        trade = TradeRecord(
            order_id="test-order-1",
            trade_timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            trade_side=TradeSide.YES,
            price_cents=72,
            market_ticker="KXMIA-25JAN01-72",
            quantity=10,
            fee_cents=5,
            cost_cents=725,
            market_category="weather",
            trade_rule="test_rule",
            trade_reason="test_reason",
            weather_station="KMIA",
        )
        strikes = [70.0, 72.0, 74.0, 76.0]
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]

        result = builder.create_executed_trade_shading(trade, strikes, timestamps)

        assert result is not None
        assert result.y_min == 72.0
        assert result.y_max == 74.0  # Next strike above 72
        assert result.color == ShadingBuilder.EXECUTED_BUY_COLOR
        assert "Executed yes" in result.label

    def test_creates_sell_shading(self) -> None:
        """Test creating shading for sell trade."""
        builder = ShadingBuilder()
        trade = TradeRecord(
            order_id="test-order-2",
            trade_timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            trade_side=TradeSide.NO,
            price_cents=75,
            market_ticker="KXMIA-25JAN01-75",
            quantity=5,
            fee_cents=3,
            cost_cents=378,
            market_category="weather",
            trade_rule="test_rule",
            trade_reason="test_reason",
            weather_station="KMIA",
        )
        strikes = [70.0, 75.0, 80.0]
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]

        result = builder.create_executed_trade_shading(trade, strikes, timestamps)

        assert result is not None
        assert result.color == ShadingBuilder.EXECUTED_SELL_COLOR
        assert "Executed no" in result.label

    def test_shading_time_window(self) -> None:
        """Test shading has 30 minute window."""
        builder = ShadingBuilder()
        trade_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        trade = TradeRecord(
            order_id="test-order-3",
            trade_timestamp=trade_time,
            trade_side=TradeSide.YES,
            price_cents=70,
            market_ticker="KXMIA-25JAN01-70",
            quantity=1,
            fee_cents=1,
            cost_cents=71,
            market_category="weather",
            trade_rule="test_rule",
            trade_reason="test_reason",
            weather_station="KMIA",
        )
        strikes = [70.0, 75.0]
        timestamps = [trade_time]

        result = builder.create_executed_trade_shading(trade, strikes, timestamps)

        assert result is not None
        assert result.start_time == trade_time - timedelta(minutes=30)
        assert result.end_time == trade_time + timedelta(minutes=30)


class TestShadingBuilderCreateNoLiquidityShading:
    """Tests for ShadingBuilder.create_no_liquidity_shading method."""

    def test_creates_shading_from_state_strikes(self) -> None:
        """Test creating shading using state strike values."""
        builder = ShadingBuilder()
        state = MagicMock()
        state.timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        state.market_ticker = "KXMIA-25JAN01"
        state.min_strike_price_cents = 70.0
        state.max_strike_price_cents = 80.0
        strikes = [70.0, 75.0, 80.0]
        timestamps = [state.timestamp]

        result = builder.create_no_liquidity_shading(state, strikes, timestamps)

        assert result is not None
        assert result.y_min == 70.0
        assert result.y_max == 80.0
        assert result.color == ShadingBuilder.UNEXECUTED_COLOR
        assert "No liquidity" in result.label

    def test_returns_none_for_empty_strikes(self) -> None:
        """Test returns None when strikes list is empty."""
        builder = ShadingBuilder()
        state = MagicMock()
        state.timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        timestamps = [state.timestamp]

        result = builder.create_no_liquidity_shading(state, [], timestamps)

        assert result is None

    def test_shading_time_window(self) -> None:
        """Test shading has 1 hour window."""
        builder = ShadingBuilder()
        state_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        state = MagicMock()
        state.timestamp = state_time
        state.market_ticker = "KXMIA-25JAN01"
        state.min_strike_price_cents = 70.0
        state.max_strike_price_cents = 80.0
        strikes = [70.0, 75.0, 80.0]
        timestamps = [state_time]

        result = builder.create_no_liquidity_shading(state, strikes, timestamps)

        assert result is not None
        assert result.start_time == state_time - timedelta(hours=1)
        assert result.end_time == state_time + timedelta(hours=1)


class TestShadingBuilderApplyTradeShadingsToChart:
    """Tests for ShadingBuilder.apply_trade_shadings_to_chart method."""

    def test_applies_multiple_shadings(self) -> None:
        """Test applying multiple shadings."""
        mock_ax = MagicMock()
        shadings = [
            TradeShading(
                start_time=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
                y_min=70.0,
                y_max=75.0,
                color="#90EE90",
                alpha=0.3,
                label="Trade 1",
            ),
            TradeShading(
                start_time=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
                y_min=75.0,
                y_max=80.0,
                color="#FFB6C1",
                alpha=0.3,
                label="Trade 2",
            ),
        ]
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]

        ShadingBuilder.apply_trade_shadings_to_chart(mock_ax, shadings, timestamps)

        assert mock_ax.axhspan.call_count == 2

    def test_applies_empty_shadings(self) -> None:
        """Test applying empty shadings list."""
        mock_ax = MagicMock()

        ShadingBuilder.apply_trade_shadings_to_chart(mock_ax, [], [])

        mock_ax.axhspan.assert_not_called()


class TestShadingBuilderConstants:
    """Tests for ShadingBuilder constants."""

    def test_executed_buy_color(self) -> None:
        """Test executed buy color constant."""
        assert ShadingBuilder.EXECUTED_BUY_COLOR == "#90EE90"

    def test_executed_sell_color(self) -> None:
        """Test executed sell color constant."""
        assert ShadingBuilder.EXECUTED_SELL_COLOR == "#FFB6C1"

    def test_unexecuted_color(self) -> None:
        """Test unexecuted color constant."""
        assert ShadingBuilder.UNEXECUTED_COLOR == "#808080"

    def test_default_alpha(self) -> None:
        """Test default alpha constant."""
        assert ShadingBuilder.DEFAULT_ALPHA == 0.3
