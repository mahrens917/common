from datetime import datetime, timezone

import pytest

from src.common.data_models.trading import (
    OrderAction,
    OrderFill,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    PortfolioBalance,
    PortfolioPosition,
)

DEFAULT_TRADE_FILLED_COUNT = 5
DEFAULT_TRADE_ECHO_PRICE = 50
DEFAULT_TRADE_FEES = 2
DEFAULT_ORDER_REMAINING_COUNT = 0
DEFAULT_ORDER_FEES = 10
SECONDARY_TRADE_FILLED_COUNT = 2
TERTIARY_TRADE_FILLED_COUNT = 3
QUATERNARY_TRADE_FILLED_COUNT = 4
MINIMAL_TRADE_FILLED_COUNT = 1
_CONST_55 = 55

from src.common.position_lifecycle_validators import (
    BalanceStateSnapshot,
    PositionStateSnapshot,
    TradeExecution,
    create_balance_snapshot,
    create_position_snapshot,
    create_trade_execution,
    validate_portfolio_balance_arithmetic,
    validate_position_exposure_limits,
    validate_position_pnl_consistency,
    validate_position_state_transition,
    validate_trade_execution_consistency,
)

BASE_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _position_state_snapshot(**overrides):
    data = {
        "ticker": "TEST",
        "position_count": 10,
        "side": OrderSide.YES,
        "unrealized_pnl_cents": 0,
        "average_price_cents": 40,
        "timestamp": BASE_TIME,
    }
    data.update(overrides)
    if "market_value_cents" not in overrides:
        data["market_value_cents"] = (
            data["position_count"] * data["average_price_cents"] + data["unrealized_pnl_cents"]
        )
    return PositionStateSnapshot(**data)


def _trade_execution(**overrides):
    data = {
        "order_id": "order-1",
        "ticker": "TEST",
        "side": OrderSide.YES,
        "action": "BUY",
        "filled_count": DEFAULT_TRADE_FILLED_COUNT,
        "average_fill_price_cents": DEFAULT_TRADE_ECHO_PRICE,
        "fees_cents": DEFAULT_TRADE_FEES,
        "timestamp": BASE_TIME,
    }
    data.update(overrides)
    return TradeExecution(**data)


def _portfolio_position(**overrides):
    data = {
        "ticker": "TEST",
        "position_count": 5,
        "side": OrderSide.YES,
        "unrealized_pnl_cents": 0,
        "average_price_cents": 40,
        "last_updated": BASE_TIME,
    }
    data.update({k: v for k, v in overrides.items() if k != "market_value_cents"})
    if "market_value_cents" in overrides:
        data["market_value_cents"] = overrides["market_value_cents"]
    else:
        data["market_value_cents"] = (
            data["position_count"] * data["average_price_cents"] + data["unrealized_pnl_cents"]
        )
    return PortfolioPosition(**data)


def _portfolio_balance(**overrides):
    data = {"balance_cents": 10_000, "timestamp": BASE_TIME, "currency": "USD"}
    data.update(overrides)
    return PortfolioBalance(**data)


def _order_response(**overrides):
    base_price = (
        overrides["average_fill_price_cents"]
        if "average_fill_price_cents" in overrides
        else DEFAULT_TRADE_ECHO_PRICE
    )
    filled_count = (
        overrides["filled_count"] if "filled_count" in overrides else DEFAULT_TRADE_FILLED_COUNT
    )
    fills_override = overrides.get("fills")
    fills = fills_override
    if fills_override is None:
        fill_price = base_price if base_price is not None else 50
        fills = []
        if filled_count > 0:
            fills = [OrderFill(price_cents=fill_price, count=filled_count, timestamp=BASE_TIME)]
    data = {
        "order_id": "order-1",
        "client_order_id": "client-1",
        "status": OrderStatus.FILLED,
        "ticker": "TEST",
        "side": OrderSide.YES,
        "action": OrderAction.BUY,
        "order_type": OrderType.MARKET,
        "filled_count": filled_count,
        "remaining_count": DEFAULT_ORDER_REMAINING_COUNT,
        "average_fill_price_cents": base_price,
        "timestamp": BASE_TIME,
        "fees_cents": DEFAULT_ORDER_FEES,
        "fills": fills,
        "trade_rule": "RULE",
        "trade_reason": "example trade",
    }
    data.update(overrides)
    if fills_override is not None:
        data["fills"] = fills_override
    return OrderResponse(**data)


def test_validate_position_state_transition_success():
    before = _position_state_snapshot(position_count=5, average_price_cents=40)
    trade = _trade_execution(
        action="BUY", filled_count=DEFAULT_TRADE_FILLED_COUNT, average_fill_price_cents=60
    )
    after = _position_state_snapshot(position_count=10, average_price_cents=50)

    is_valid, message = validate_position_state_transition(before, after, trade)
    assert is_valid, message


def test_validate_position_state_transition_average_price_error():
    before = _position_state_snapshot(position_count=5, average_price_cents=40)
    trade = _trade_execution(
        action="BUY", filled_count=DEFAULT_TRADE_FILLED_COUNT, average_fill_price_cents=60
    )
    after = _position_state_snapshot(position_count=10, average_price_cents=55)

    is_valid, message = validate_position_state_transition(before, after, trade)
    assert not is_valid
    assert "Average price" in message


def test_validate_portfolio_balance_arithmetic_success():
    before = BalanceStateSnapshot(balance_cents=10_000, timestamp=BASE_TIME)
    after = BalanceStateSnapshot(balance_cents=9_866, timestamp=BASE_TIME)
    trades = [
        _trade_execution(
            action="BUY", filled_count=DEFAULT_TRADE_FILLED_COUNT, average_fill_price_cents=50
        ),
        _trade_execution(
            action="SELL", filled_count=SECONDARY_TRADE_FILLED_COUNT, average_fill_price_cents=60
        ),
    ]

    is_valid, message = validate_portfolio_balance_arithmetic(before, after, trades)
    assert is_valid, message


def test_validate_portfolio_balance_arithmetic_mismatch():
    before = BalanceStateSnapshot(balance_cents=10_000, timestamp=BASE_TIME)
    after = BalanceStateSnapshot(balance_cents=9_600, timestamp=BASE_TIME)
    trades = [
        _trade_execution(
            action="BUY", filled_count=DEFAULT_TRADE_FILLED_COUNT, average_fill_price_cents=50
        )
    ]

    is_valid, message = validate_portfolio_balance_arithmetic(before, after, trades)
    assert not is_valid
    assert "Balance arithmetic mismatch" in message


def test_validate_position_state_transition_sell():
    before = _position_state_snapshot(position_count=8, average_price_cents=40)
    trade = _trade_execution(
        action="SELL",
        filled_count=TERTIARY_TRADE_FILLED_COUNT,
        average_fill_price_cents=55,
    )
    after = _position_state_snapshot(position_count=5, average_price_cents=40)

    is_valid, message = validate_position_state_transition(before, after, trade)
    assert is_valid, message


def test_validate_position_state_transition_first_position_average_price_mismatch():
    trade = _trade_execution(
        action="BUY",
        filled_count=SECONDARY_TRADE_FILLED_COUNT,
        average_fill_price_cents=70,
    )
    after = _position_state_snapshot(position_count=2, average_price_cents=65)

    is_valid, message = validate_position_state_transition(None, after, trade)
    assert not is_valid
    assert "First position average price mismatch" in message


def test_validate_position_state_transition_invalid_action():
    before = _position_state_snapshot(position_count=5, average_price_cents=40)
    trade = _trade_execution(action="HOLD")
    after = _position_state_snapshot(position_count=5, average_price_cents=40)

    is_valid, message = validate_position_state_transition(before, after, trade)
    assert not is_valid
    assert "Invalid trade action" in message


def test_validate_portfolio_balance_arithmetic_invalid_action():
    before = BalanceStateSnapshot(balance_cents=10_000, timestamp=BASE_TIME)
    after = BalanceStateSnapshot(balance_cents=9_900, timestamp=BASE_TIME)
    trades = [_trade_execution(action="HOLD")]

    is_valid, message = validate_portfolio_balance_arithmetic(before, after, trades)
    assert not is_valid
    assert "Invalid trade action" in message


def test_validate_position_pnl_consistency_success():
    position = _portfolio_position(unrealized_pnl_cents=30)

    is_valid, message = validate_position_pnl_consistency(position)
    assert is_valid, message


def test_validate_position_pnl_consistency_failure():
    position = _portfolio_position(market_value_cents=1234)

    is_valid, message = validate_position_pnl_consistency(position)
    assert not is_valid
    assert "P&L arithmetic inconsistent" in message


def test_validate_position_exposure_limits_within_bounds():
    position = _portfolio_position(market_value_cents=4_000)

    is_valid, message = validate_position_exposure_limits(position, max_exposure_cents=5_000)
    assert is_valid, message


def test_validate_position_exposure_limits_exceeds_limit():
    position = _portfolio_position(market_value_cents=7_500)

    is_valid, message = validate_position_exposure_limits(position, max_exposure_cents=5_000)
    assert not is_valid
    assert "Position exposure exceeds limit" in message


def test_validate_trade_execution_consistency_success():
    response = _order_response(
        filled_count=QUATERNARY_TRADE_FILLED_COUNT, average_fill_price_cents=45, fees_cents=12
    )

    is_valid, message = validate_trade_execution_consistency(
        response, expected_ticker="TEST", expected_side=OrderSide.YES, expected_action="BUY"
    )
    assert is_valid, message


def test_validate_trade_execution_consistency_action_mismatch():
    response = _order_response(action=OrderAction.BUY)

    is_valid, message = validate_trade_execution_consistency(
        response, expected_ticker="TEST", expected_side=OrderSide.YES, expected_action="SELL"
    )
    assert not is_valid
    assert "Action mismatch" in message


def test_validate_trade_execution_consistency_missing_price():
    response = _order_response(average_fill_price_cents=None)

    is_valid, message = validate_trade_execution_consistency(
        response, expected_ticker="TEST", expected_side=OrderSide.YES, expected_action="BUY"
    )
    assert not is_valid
    assert "Missing average fill price" in message


def test_validate_trade_execution_consistency_excessive_fees():
    response = _order_response(
        filled_count=MINIMAL_TRADE_FILLED_COUNT, average_fill_price_cents=10, fees_cents=50
    )

    is_valid, message = validate_trade_execution_consistency(
        response, expected_ticker="TEST", expected_side=OrderSide.YES, expected_action="BUY"
    )
    assert not is_valid
    assert "Excessive fees" in message


def test_create_position_snapshot_copies_portfolio_attributes():
    position = _portfolio_position(
        position_count=3, average_price_cents=35, unrealized_pnl_cents=15, market_value_cents=120
    )

    snapshot = create_position_snapshot(position)
    assert snapshot.ticker == position.ticker
    assert snapshot.position_count == position.position_count
    assert snapshot.unrealized_pnl_cents == position.unrealized_pnl_cents
    assert snapshot.average_price_cents == position.average_price_cents
    assert snapshot.timestamp is position.last_updated


def test_create_balance_snapshot_copies_balance_attributes():
    balance = _portfolio_balance(balance_cents=9_500)

    snapshot = create_balance_snapshot(balance)
    assert snapshot.balance_cents == balance.balance_cents
    assert snapshot.timestamp is balance.timestamp


def test_create_trade_execution_builds_from_order_response():
    response = _order_response(
        side=OrderSide.NO,
        filled_count=TERTIARY_TRADE_FILLED_COUNT,
        average_fill_price_cents=55,
        fees_cents=6,
    )

    execution = create_trade_execution(response, ticker="TEST", side=OrderSide.NO, action="SELL")
    assert execution.order_id == response.order_id
    assert execution.ticker == "TEST"
    assert execution.side is OrderSide.NO
    assert execution.action == "SELL"
    assert execution.average_fill_price_cents == _CONST_55


def test_create_trade_execution_requires_average_price():
    response = _order_response(average_fill_price_cents=None)

    with pytest.raises(ValueError, match="missing average fill price"):
        create_trade_execution(response, ticker="TEST", side=OrderSide.YES, action="BUY")
