from datetime import datetime

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
    TradeRule,
    TradingError,
)

_CENTS_150000 = 1_500_00
ZERO_FILL_COUNT = 0
DEFAULT_RESPONSE_FILL_COUNT = 2
DEFAULT_RESPONSE_REMAINING = 1
ALTERNATE_RESPONSE_FILL_COUNT = 3


def _now() -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0)


def test_portfolio_balance_validation():
    balance = PortfolioBalance(balance_cents=1_500_00, timestamp=_now(), currency="USD")
    assert balance.balance_cents == _CENTS_150000

    with pytest.raises(ValueError, match="cannot be negative"):
        PortfolioBalance(balance_cents=-1, timestamp=_now(), currency="USD")

    with pytest.raises(ValueError, match="Only USD"):
        PortfolioBalance(balance_cents=100, timestamp=_now(), currency="EUR")

    with pytest.raises(TypeError, match="Timestamp must be a datetime"):
        PortfolioBalance(balance_cents=100, timestamp="2024-01-01", currency="USD")  # type: ignore[arg-type]


def test_portfolio_position_validation_errors():
    with pytest.raises(ValueError, match="Ticker must be specified"):
        PortfolioPosition(
            ticker="",
            position_count=1,
            side=OrderSide.YES,
            market_value_cents=10,
            unrealized_pnl_cents=0,
            average_price_cents=50,
            last_updated=_now(),
        )

    with pytest.raises(ValueError, match="Position count cannot be zero"):
        PortfolioPosition(
            ticker="KXTEST",
            position_count=0,
            side=OrderSide.YES,
            market_value_cents=10,
            unrealized_pnl_cents=0,
            average_price_cents=50,
            last_updated=_now(),
        )

    with pytest.raises(ValueError, match="Average price must be between 1-100 cents"):
        PortfolioPosition(
            ticker="KXTEST",
            position_count=1,
            side=OrderSide.YES,
            market_value_cents=10,
            unrealized_pnl_cents=0,
            average_price_cents=0,
            last_updated=_now(),
        )


def test_order_request_limit_and_market_validation():
    with pytest.raises(ValueError, match="Market orders must specify yes_price_cents"):
        OrderRequest(
            ticker="KXTEST",
            action=OrderAction.BUY,
            side=OrderSide.YES,
            count=10,
            client_order_id="abc",
            trade_rule=TradeRule.TEMP_DECLINE.value,
            trade_reason="weather cooling trend",
            order_type=OrderType.MARKET,
            yes_price_cents=None,
        )

    OrderRequest(
        ticker="KXTEST",
        action=OrderAction.BUY,
        side=OrderSide.YES,
        count=10,
        client_order_id="abc",
        trade_rule=TradeRule.TEMP_DECLINE.value,
        trade_reason="weather cooling trend",
        order_type=OrderType.MARKET,
        yes_price_cents=0,
    )

    with pytest.raises(ValueError, match="Limit orders must specify yes_price_cents"):
        OrderRequest(
            ticker="KXTEST",
            action=OrderAction.BUY,
            side=OrderSide.YES,
            count=1,
            client_order_id="abc",
            trade_rule=TradeRule.TEMP_INCREASE.value,
            trade_reason="warming trend analysis",
            order_type=OrderType.LIMIT,
            yes_price_cents=None,
        )

    with pytest.raises(ValueError, match="must be descriptive"):
        OrderRequest(
            ticker="KXTEST",
            action=OrderAction.SELL,
            side=OrderSide.NO,
            count=1,
            client_order_id="xyz",
            trade_rule="RULE",
            trade_reason="short",
            order_type=OrderType.MARKET,
            yes_price_cents=0,
        )


def test_order_fill_validation():
    fill = OrderFill(price_cents=10, count=1, timestamp=_now())
    assert fill.count == 1

    with pytest.raises(ValueError, match="Fill price must be between 1-99 cents"):
        OrderFill(price_cents=0, count=1, timestamp=_now())

    with pytest.raises(ValueError, match="Fill count must be positive"):
        OrderFill(price_cents=10, count=0, timestamp=_now())


def test_order_response_validations():
    fills = [OrderFill(price_cents=20, count=2, timestamp=_now())]
    OrderResponse(
        order_id="123",
        client_order_id="abc",
        status=OrderStatus.PARTIALLY_FILLED,
        ticker="KXTEST",
        side=OrderSide.YES,
        action=OrderAction.BUY,
        order_type=OrderType.LIMIT,
        filled_count=DEFAULT_RESPONSE_FILL_COUNT,
        remaining_count=DEFAULT_RESPONSE_REMAINING,
        average_fill_price_cents=None,
        timestamp=_now(),
        fees_cents=0,
        fills=fills,
        trade_rule=TradeRule.TEMP_DECLINE.value,
        trade_reason="extended chill pattern",
    )

    with pytest.raises(ValueError, match="Sum of fill counts"):
        OrderResponse(
            order_id="123",
            client_order_id="abc",
            status=OrderStatus.FILLED,
            ticker="KXTEST",
            side=OrderSide.YES,
            action=OrderAction.BUY,
            order_type=OrderType.LIMIT,
            filled_count=ALTERNATE_RESPONSE_FILL_COUNT,
            remaining_count=0,
            average_fill_price_cents=10,
            timestamp=_now(),
            fees_cents=0,
            fills=fills,
            trade_rule=TradeRule.TEMP_DECLINE.value,
            trade_reason="extended chill pattern",
        )

    with pytest.raises(ValueError, match="cannot be negative"):
        OrderResponse(
            order_id="bad-fees",
            client_order_id="abc",
            status=OrderStatus.CANCELLED,
            ticker="KXTEST",
            side=OrderSide.NO,
            action=OrderAction.SELL,
            order_type=OrderType.MARKET,
            filled_count=ZERO_FILL_COUNT,
            remaining_count=1,
            average_fill_price_cents=None,
            timestamp=_now(),
            fees_cents=-1,
            fills=[],
            trade_rule="RULE",
            trade_reason="cancellation helps",
        )


def test_trading_error_validation():
    TradingError(
        error_code="E123",
        error_message="Failure",
        timestamp=_now(),
        operation_name="submit_order",
        request_data={"ticker": "KXTEST"},
    )

    with pytest.raises(ValueError, match="Error code must be specified"):
        TradingError(error_code="", error_message="x", timestamp=_now(), operation_name="op")

    with pytest.raises(ValueError, match="Error message must be specified"):
        TradingError(error_code="E1", error_message="", timestamp=_now(), operation_name="op")


def test_market_validation_data_checks():
    data = MarketValidationData(
        ticker="KXTEST",
        is_open=True,
        best_bid_cents=10,
        best_ask_cents=20,
        last_price_cents=15,
        timestamp=_now(),
    )
    assert data.is_open is True

    with pytest.raises(ValueError, match="Best bid"):
        MarketValidationData(
            ticker="KXTEST",
            is_open=True,
            best_bid_cents=100,
            best_ask_cents=20,
            last_price_cents=15,
            timestamp=_now(),
        )

    with pytest.raises(ValueError, match="must be less than best ask"):
        MarketValidationData(
            ticker="KXTEST",
            is_open=True,
            best_bid_cents=20,
            best_ask_cents=20,
            last_price_cents=15,
            timestamp=_now(),
        )
