from __future__ import annotations

from datetime import datetime, timezone

import pytest

from common.data_models.trading import (
    MarketValidationData,
    OrderAction,
    OrderFill,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    PortfolioBalance,
    PortfolioPosition,
    TimeInForce,
    TradingError,
)

_CONST_10000 = 10_000
_CONST_40 = 40
_CONST_45 = 45
_CONST_NEG_200 = -200
DEFAULT_ORDER_COUNT = 1
DEFAULT_FILL_PRICE = 40
FILLED_COUNT_ZERO = 0
FILLED_COUNT_ONE = 1
FILLED_COUNT_TWO = 2


def utc_now():
    return datetime(2024, 8, 20, 12, tzinfo=timezone.utc)


def test_portfolio_balance_validation():
    balance = PortfolioBalance(balance_cents=10_000, timestamp=utc_now(), currency="USD")
    assert balance.balance_cents == _CONST_10000

    with pytest.raises(ValueError):
        PortfolioBalance(balance_cents=-1, timestamp=utc_now(), currency="USD")

    with pytest.raises(ValueError):
        PortfolioBalance(balance_cents=10, timestamp=utc_now(), currency="EUR")


def test_portfolio_position_validation():
    position = PortfolioPosition(
        ticker="KX-TEST",
        position_count=1,
        side=OrderSide.YES,
        market_value_cents=50,
        unrealized_pnl_cents=5,
        average_price_cents=40,
        last_updated=utc_now(),
    )
    assert position.side is OrderSide.YES

    with pytest.raises(ValueError):
        PortfolioPosition(
            ticker="",
            position_count=1,
            side=OrderSide.YES,
            market_value_cents=50,
            unrealized_pnl_cents=5,
            average_price_cents=40,
            last_updated=utc_now(),
        )

    short_position = PortfolioPosition(
        ticker="KX-TEST",
        position_count=-2,
        side=OrderSide.NO,
        market_value_cents=-200,
        unrealized_pnl_cents=-40,
        average_price_cents=40,
        last_updated=utc_now(),
    )
    assert short_position.market_value_cents == _CONST_NEG_200


def test_order_request_limit_price_validation():
    req = OrderRequest(
        ticker="KX-TEST",
        action=OrderAction.BUY,
        side=OrderSide.YES,
        count=DEFAULT_ORDER_COUNT,
        client_order_id="abc",
        trade_rule="RULE",
        trade_reason="Weather driven entry",
        order_type=OrderType.LIMIT,
        yes_price_cents=45,
    )
    assert req.yes_price_cents == _CONST_45

    with pytest.raises(ValueError):
        OrderRequest(
            ticker="KX",
            action=OrderAction.BUY,
            side=OrderSide.YES,
            count=1,
            client_order_id="id",
            trade_rule="RULE",
            trade_reason="Too short",
            order_type=OrderType.MARKET,
            yes_price_cents=0,
        )

    with pytest.raises(TypeError):
        OrderRequest(
            ticker="KX",
            action=OrderAction.BUY,
            side=OrderSide.YES,
            count=1,
            client_order_id="id",
            trade_rule="RULE",
            trade_reason="Weather driven entry",
            order_type=OrderType.MARKET,
            time_in_force="IOC",  # type: ignore[arg-type]
            yes_price_cents=0,
        )


def test_order_response_validation():
    fills = [OrderFill(price_cents=40, count=1, timestamp=utc_now())]
    resp = OrderResponse(
        order_id="123",
        client_order_id="abc",
        status=OrderStatus.FILLED,
        ticker="KX",
        side=OrderSide.YES,
        action=OrderAction.BUY,
        order_type=OrderType.LIMIT,
        filled_count=FILLED_COUNT_ONE,
        remaining_count=0,
        average_fill_price_cents=DEFAULT_FILL_PRICE,
        timestamp=utc_now(),
        fees_cents=2,
        fills=fills,
        trade_rule="RULE",
        trade_reason="Weather driven entry",
    )
    assert resp.filled_count == FILLED_COUNT_ONE
    assert resp.average_fill_price_cents == _CONST_40

    with pytest.raises(ValueError):
        OrderResponse(
            order_id="123",
            client_order_id="abc",
            status=OrderStatus.PARTIALLY_FILLED,
            ticker="KX",
            side=OrderSide.YES,
            action=OrderAction.BUY,
            order_type=OrderType.LIMIT,
            filled_count=FILLED_COUNT_ZERO,
            remaining_count=1,
            average_fill_price_cents=None,
            timestamp=utc_now(),
            fees_cents=0,
            fills=[],
            trade_rule="RULE",
            trade_reason="Weather driven entry",
        )

    with pytest.raises(ValueError):
        OrderResponse(
            order_id="123",
            client_order_id="abc",
            status=OrderStatus.FILLED,
            ticker="KX",
            side=OrderSide.YES,
            action=OrderAction.BUY,
            order_type=OrderType.LIMIT,
            filled_count=FILLED_COUNT_ONE,
            remaining_count=0,
            average_fill_price_cents=120,
            timestamp=utc_now(),
            fees_cents=0,
            fills=fills,
            trade_rule="RULE",
            trade_reason="Weather driven entry",
        )

    with pytest.raises(ValueError):
        OrderResponse(
            order_id="123",
            client_order_id="abc",
            status=OrderStatus.FILLED,
            ticker="KX",
            side=OrderSide.YES,
            action=OrderAction.BUY,
            order_type=OrderType.LIMIT,
            filled_count=FILLED_COUNT_TWO,
            remaining_count=0,
            average_fill_price_cents=40,
            timestamp=utc_now(),
            fees_cents=0,
            fills=[OrderFill(price_cents=40, count=1, timestamp=utc_now())],
            trade_rule="RULE",
            trade_reason="Weather driven entry",
        )


def test_market_validation_data_enforces_spread():
    with pytest.raises(ValueError):
        MarketValidationData(
            ticker="KX",
            is_open=True,
            best_bid_cents=90,
            best_ask_cents=80,
            last_price_cents=85,
            timestamp=utc_now(),
        )

    mv = MarketValidationData(
        ticker="KX",
        is_open=True,
        best_bid_cents=40,
        best_ask_cents=60,
        last_price_cents=50,
        timestamp=utc_now(),
    )
    assert mv.best_bid_cents == _CONST_40


def test_order_fill_validation():
    fill = OrderFill(price_cents=50, count=1, timestamp=utc_now())
    assert fill.count == 1

    with pytest.raises(ValueError):
        OrderFill(price_cents=0, count=1, timestamp=utc_now())

    with pytest.raises(ValueError):
        OrderFill(price_cents=50, count=0, timestamp=utc_now())

    with pytest.raises(TypeError):
        OrderFill(price_cents=50, count=1, timestamp="bad")  # type: ignore[arg-type]


def test_trading_error_validation():
    error = TradingError(
        error_code="ERR",
        error_message="Oops",
        timestamp=utc_now(),
        operation_name="op",
    )
    assert error.error_message == "Oops"

    with pytest.raises(ValueError):
        TradingError(
            error_code="",
            error_message="",
            timestamp=utc_now(),
            operation_name="op",
        )
