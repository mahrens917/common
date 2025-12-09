from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.common.data_models.trade_record import (
    TradeRecord,
    TradeSide,
    get_trade_close_date,
    is_trade_reason_valid,
)


def _make_trade(**overrides) -> TradeRecord:
    base = dict(
        order_id="order-1",
        market_ticker="KX-TEST",
        trade_timestamp=datetime(2024, 8, 20, tzinfo=timezone.utc),
        trade_side=TradeSide.YES,
        quantity=2,
        price_cents=40,
        fee_cents=4,
        cost_cents=(40 * 2) + 4,
        market_category="weather",
        trade_rule="rule-1",
        trade_reason="Weather driven entry",
        weather_station="kjfk",
    )
    base.update(overrides)
    return TradeRecord(**base)


def test_is_trade_reason_valid_variants():
    assert is_trade_reason_valid("  Weather driven entry  ")
    assert is_trade_reason_valid("Storm")  # permitted short reason
    assert not is_trade_reason_valid("")
    assert not is_trade_reason_valid("short")


def test_get_trade_close_date_prefers_settlement_time():
    trade = _make_trade()
    assert get_trade_close_date(trade) == trade.trade_timestamp.date()

    settlement_time = trade.trade_timestamp + timedelta(days=1)
    trade.settlement_time = settlement_time
    assert get_trade_close_date(trade) == settlement_time.date()


def test_trade_record_validation_and_normalisation():
    trade = _make_trade()
    assert trade.market_category == "weather"
    assert trade.weather_station == "KJFK"
    assert trade.is_settled is False

    trade.settlement_price_cents = 60
    assert trade.realised_pnl_cents() == (60 * trade.quantity) - trade.cost_cents


def test_trade_record_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        _make_trade(order_id="")

    with pytest.raises(ValueError):
        _make_trade(quantity=0)

    with pytest.raises(ValueError):
        _make_trade(price_cents=0)

    with pytest.raises(ValueError):
        _make_trade(fee_cents=-1)

    with pytest.raises(ValueError):
        _make_trade(cost_cents=999)

    with pytest.raises(ValueError):
        _make_trade(market_category="invalid")

    with pytest.raises(ValueError):
        _make_trade(weather_station=None)

    with pytest.raises(ValueError):
        _make_trade(trade_reason="short")

    with pytest.raises(ValueError):
        _make_trade(settlement_price_cents=200)

    with pytest.raises(ValueError):
        _make_trade(settlement_time="bad")  # type: ignore[arg-type]
