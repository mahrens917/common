from datetime import datetime, timedelta, timezone

import pytest

from common.data_models.trade_record import (
    TradeRecord,
    TradeSide,
    get_trade_close_date,
)

BASE_TIMESTAMP = datetime(2024, 1, 3, 10, 15, tzinfo=timezone.utc)


def _make_trade(**overrides) -> TradeRecord:
    data = {
        "order_id": "order-1",
        "market_ticker": "KXHIGH-KJFK",
        "trade_timestamp": BASE_TIMESTAMP,
        "trade_side": TradeSide.YES,
        "quantity": 3,
        "price_cents": 20,
        "fee_cents": 2,
        "market_category": "weather",
        "weather_station": "KJFK",
        "trade_rule": "rule_3",
        "trade_reason": "initial-entry",
        "last_yes_bid": None,
        "last_yes_ask": None,
        "last_price_update": None,
        "settlement_price_cents": None,
        "settlement_time": None,
    }
    for key, value in overrides.items():
        if key != "cost_cents":
            data[key] = value

    data["cost_cents"] = overrides.get(
        "cost_cents",
        data["price_cents"] * data["quantity"] + data["fee_cents"],
    )

    return TradeRecord(**data)


def test_get_trade_close_date_prefers_settlement_time():
    settlement_time = BASE_TIMESTAMP + timedelta(days=1)
    trade = _make_trade(settlement_time=settlement_time, settlement_price_cents=52)

    assert get_trade_close_date(trade) == settlement_time.date()


def test_get_trade_close_date_falls_back_to_trade_timestamp():
    trade = _make_trade()

    assert get_trade_close_date(trade) == BASE_TIMESTAMP.date()


def test_trade_record_validates_cost_mismatch():
    with pytest.raises(ValueError, match="Cost mismatch"):
        TradeRecord(
            order_id="order-9",
            market_ticker="KXHIGH-TEST",
            trade_timestamp=BASE_TIMESTAMP,
            trade_side=TradeSide.YES,
            quantity=2,
            price_cents=30,
            fee_cents=5,
            cost_cents=1000,
            market_category="weather",
            weather_station="KORD",
            trade_rule="rule_4",
            trade_reason="manual-adjustment",
        )


def test_trade_record_requires_market_category():
    with pytest.raises(ValueError, match="Market category must be specified"):
        _make_trade(market_category="")


def test_trade_record_rejects_unknown_category():
    with pytest.raises(ValueError, match="Unsupported market category"):
        _make_trade(market_category="unknown")


def test_trade_record_rejects_invalid_settlement_price():
    with pytest.raises(ValueError, match="Settlement price must be between 0 and 100 cents"):
        _make_trade(settlement_price_cents=120)


def test_realised_pnl_yes_side():
    trade = _make_trade(settlement_price_cents=80)

    assert trade.realised_pnl_cents() == (80 * 3) - trade.cost_cents


def test_realised_pnl_no_side():
    trade = _make_trade(trade_side=TradeSide.NO, settlement_price_cents=30)

    assert trade.realised_pnl_cents() == ((100 - 30) * 3) - trade.cost_cents


def test_realised_pnl_returns_none_when_unsettled():
    trade = _make_trade()

    assert trade.realised_pnl_cents() is None


def test_calculate_current_pnl_prefers_realised_value_when_settled():
    trade = _make_trade(settlement_price_cents=70, last_yes_bid=15)

    assert trade.calculate_current_pnl_cents() == trade.realised_pnl_cents()


def test_calculate_current_pnl_uses_live_market_price_yes():
    trade = _make_trade(last_yes_bid=45.6)

    assert trade.calculate_current_pnl_cents() == (46 * 3) - trade.cost_cents


def test_calculate_current_pnl_uses_live_market_price_for_no_side():
    trade = _make_trade(trade_side=TradeSide.NO, last_yes_ask="36.4")

    assert trade.calculate_current_pnl_cents() == (64 * 3) - trade.cost_cents


def test_calculate_current_pnl_errors_when_market_price_missing():
    trade = _make_trade(last_yes_bid="")

    with pytest.raises(RuntimeError):
        trade.calculate_current_pnl_cents()


def test_trade_record_allows_non_weather_without_station():
    trade = _make_trade(
        market_category="binary",
        market_ticker="KXBTC-25APR01",
        weather_station=None,
        trade_rule="EMERGENCY_EXIT",
        trade_reason="Emergency exit flow",
    )

    assert trade.market_category == "binary"
    assert trade.weather_station is None
