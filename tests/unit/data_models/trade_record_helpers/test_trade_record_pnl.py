"""Tests for trade_record_pnl module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from common.data_models.trade_record import TradeSide
from common.data_models.trade_record_helpers.trade_record_pnl import (
    ERR_INVALID_PNL_VALUE,
    calculate_current_pnl_cents,
    calculate_realised_pnl_cents,
    get_current_market_price_cents,
)


class TestCalculateRealisedPnlCents:
    """Tests for calculate_realised_pnl_cents function."""

    def test_returns_none_when_settlement_price_is_none(self) -> None:
        """Returns None when settlement price is None."""
        result = calculate_realised_pnl_cents(
            settlement_price_cents=None,
            trade_side=TradeSide.YES,
            quantity=10,
            cost_cents=500,
        )

        assert result is None

    def test_calculates_profit_for_yes_side_when_settled_at_100(self) -> None:
        """Calculates profit for YES side when settled at 100."""
        # Bought YES at 50 cents, quantity 10, cost 500
        # Settled at 100 cents, final value = 100 * 10 = 1000
        # PnL = 1000 - 500 = 500
        result = calculate_realised_pnl_cents(
            settlement_price_cents=100,
            trade_side=TradeSide.YES,
            quantity=10,
            cost_cents=500,
        )

        assert result == 500

    def test_calculates_loss_for_yes_side_when_settled_at_0(self) -> None:
        """Calculates loss for YES side when settled at 0."""
        # Bought YES at 50 cents, quantity 10, cost 500
        # Settled at 0 cents, final value = 0 * 10 = 0
        # PnL = 0 - 500 = -500
        result = calculate_realised_pnl_cents(
            settlement_price_cents=0,
            trade_side=TradeSide.YES,
            quantity=10,
            cost_cents=500,
        )

        assert result == -500

    def test_calculates_profit_for_no_side_when_settled_at_0(self) -> None:
        """Calculates profit for NO side when settled at 0."""
        # Bought NO at 50 cents (yes price), quantity 10, cost 500
        # Settled at 0 cents, final value = (100 - 0) * 10 = 1000
        # PnL = 1000 - 500 = 500
        result = calculate_realised_pnl_cents(
            settlement_price_cents=0,
            trade_side=TradeSide.NO,
            quantity=10,
            cost_cents=500,
        )

        assert result == 500

    def test_calculates_loss_for_no_side_when_settled_at_100(self) -> None:
        """Calculates loss for NO side when settled at 100."""
        # Bought NO at 50 cents (yes price), quantity 10, cost 500
        # Settled at 100 cents, final value = (100 - 100) * 10 = 0
        # PnL = 0 - 500 = -500
        result = calculate_realised_pnl_cents(
            settlement_price_cents=100,
            trade_side=TradeSide.NO,
            quantity=10,
            cost_cents=500,
        )

        assert result == -500

    def test_calculates_breakeven_for_yes_side(self) -> None:
        """Calculates breakeven for YES side."""
        # Bought YES at 50 cents, quantity 10, cost 500
        # Settled at 50 cents, final value = 50 * 10 = 500
        # PnL = 500 - 500 = 0
        result = calculate_realised_pnl_cents(
            settlement_price_cents=50,
            trade_side=TradeSide.YES,
            quantity=10,
            cost_cents=500,
        )

        assert result == 0

    def test_calculates_breakeven_for_no_side(self) -> None:
        """Calculates breakeven for NO side."""
        # Bought NO at 50 cents (yes price), quantity 10, cost 500
        # Settled at 50 cents, final value = (100 - 50) * 10 = 500
        # PnL = 500 - 500 = 0
        result = calculate_realised_pnl_cents(
            settlement_price_cents=50,
            trade_side=TradeSide.NO,
            quantity=10,
            cost_cents=500,
        )

        assert result == 0


class TestGetCurrentMarketPriceCents:
    """Tests for get_current_market_price_cents function."""

    def test_returns_yes_bid_for_yes_side(self) -> None:
        """Returns last_yes_bid for YES side."""
        result = get_current_market_price_cents(
            trade_side=TradeSide.YES,
            last_yes_bid=55.0,
            last_yes_ask=60.0,
        )

        assert result == 55

    def test_returns_none_when_yes_bid_is_none_for_yes_side(self) -> None:
        """Returns None when last_yes_bid is None for YES side."""
        result = get_current_market_price_cents(
            trade_side=TradeSide.YES,
            last_yes_bid=None,
            last_yes_ask=60.0,
        )

        assert result is None

    def test_returns_100_minus_ask_for_no_side(self) -> None:
        """Returns 100 - last_yes_ask for NO side."""
        # If ask is 60, NO side liquidation value is 100 - 60 = 40
        result = get_current_market_price_cents(
            trade_side=TradeSide.NO,
            last_yes_bid=55.0,
            last_yes_ask=60.0,
        )

        assert result == 40

    def test_returns_none_when_yes_ask_is_none_for_no_side(self) -> None:
        """Returns None when last_yes_ask is None for NO side."""
        result = get_current_market_price_cents(
            trade_side=TradeSide.NO,
            last_yes_bid=55.0,
            last_yes_ask=None,
        )

        assert result is None

    def test_rounds_floating_point_price(self) -> None:
        """Rounds floating point price to nearest integer."""
        result = get_current_market_price_cents(
            trade_side=TradeSide.YES,
            last_yes_bid=55.7,
            last_yes_ask=60.0,
        )

        assert result == 56

    def test_handles_empty_string_bid(self) -> None:
        """Handles empty string bid by returning None."""
        result = get_current_market_price_cents(
            trade_side=TradeSide.YES,
            last_yes_bid="",
            last_yes_ask=60.0,
        )

        assert result is None

    def test_handles_invalid_type_for_price(self) -> None:
        """Handles invalid type for price by returning None."""
        result = get_current_market_price_cents(
            trade_side=TradeSide.YES,
            last_yes_bid="not_a_number",
            last_yes_ask=60.0,
        )

        assert result is None


class TestCalculateCurrentPnlCents:
    """Tests for calculate_current_pnl_cents function."""

    def test_returns_realised_pnl_when_settled(self) -> None:
        """Returns realised P&L when market is settled."""
        trade = MagicMock()
        trade.settlement_price_cents = 100
        trade.trade_side = TradeSide.YES
        trade.quantity = 10
        trade.cost_cents = 500

        result = calculate_current_pnl_cents(trade)

        # final_value = 100 * 10 = 1000, PnL = 1000 - 500 = 500
        assert result == 500

    def test_returns_current_pnl_when_not_settled(self) -> None:
        """Returns current P&L based on live prices when not settled."""
        trade = MagicMock()
        trade.settlement_price_cents = None
        trade.trade_side = TradeSide.YES
        trade.quantity = 10
        trade.cost_cents = 500
        trade.last_yes_bid = 70.0
        trade.last_yes_ask = 75.0
        trade.market_ticker = "TEST-MARKET"

        result = calculate_current_pnl_cents(trade)

        # current_price = 70, value = 70 * 10 = 700, PnL = 700 - 500 = 200
        assert result == 200

    def test_raises_when_no_live_price_available(self) -> None:
        """Raises RuntimeError when live price not available and not settled."""
        trade = MagicMock()
        trade.settlement_price_cents = None
        trade.trade_side = TradeSide.YES
        trade.quantity = 10
        trade.cost_cents = 500
        trade.last_yes_bid = None
        trade.last_yes_ask = None
        trade.market_ticker = "TEST-MARKET"

        with pytest.raises(RuntimeError) as exc_info:
            calculate_current_pnl_cents(trade)

        assert "Live market price unavailable" in str(exc_info.value)
        assert "TEST-MARKET" in str(exc_info.value)

    def test_calculates_pnl_for_no_side(self) -> None:
        """Calculates P&L for NO side with live prices."""
        trade = MagicMock()
        trade.settlement_price_cents = None
        trade.trade_side = TradeSide.NO
        trade.quantity = 10
        trade.cost_cents = 500
        trade.last_yes_bid = 55.0
        trade.last_yes_ask = 60.0
        trade.market_ticker = "TEST-MARKET"

        result = calculate_current_pnl_cents(trade)

        # current_price = 100 - 60 = 40, value = 40 * 10 = 400, PnL = 400 - 500 = -100
        assert result == -100

    def test_prioritizes_realised_over_current(self) -> None:
        """Returns realised P&L even when live prices available."""
        trade = MagicMock()
        trade.settlement_price_cents = 0  # Settled at 0
        trade.trade_side = TradeSide.YES
        trade.quantity = 10
        trade.cost_cents = 500
        trade.last_yes_bid = 99.0  # Would give positive P&L if used
        trade.last_yes_ask = 100.0

        result = calculate_current_pnl_cents(trade)

        # Should use settlement, not live price
        # final_value = 0 * 10 = 0, PnL = 0 - 500 = -500
        assert result == -500


class TestErrorMessageConstants:
    """Tests for error message constants."""

    def test_err_invalid_pnl_value_exists(self) -> None:
        """ERR_INVALID_PNL_VALUE constant exists."""
        assert ERR_INVALID_PNL_VALUE
        assert "{value}" in ERR_INVALID_PNL_VALUE
