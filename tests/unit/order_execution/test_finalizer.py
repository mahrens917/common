from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Optional

import pytest

from common.data_models.trading import (
    OrderAction,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
)

_TEST_COUNT_2 = 2
DEFAULT_FINALIZER_FILLED_COUNT = 2
DEFAULT_FINALIZER_REMAINING_COUNT = 0
DEFAULT_FINALIZER_AVG_PRICE = 45

from common.order_execution import PollingOutcome, TradeFinalizer
from common.trading_exceptions import (
    KalshiTradeNotificationError,
    KalshiTradePersistenceError,
)


def _build_order_request(**overrides) -> OrderRequest:
    base = {
        "ticker": "KXHIGHNYC-25JAN01",
        "action": OrderAction.BUY,
        "side": OrderSide.YES,
        "count": 3,
        "client_order_id": "CID-1",
        "trade_rule": "RULE_ONE",
        "trade_reason": "Valid trade reason",
        "order_type": OrderType.LIMIT,
        "yes_price_cents": 45,
    }
    base.update(overrides)
    return OrderRequest(**base)


def _build_order_response(**overrides) -> OrderResponse:
    base = {
        "order_id": "ORD-1",
        "client_order_id": "CID-1",
        "status": OrderStatus.FILLED,
        "ticker": "KXHIGHNYC-25JAN01",
        "side": OrderSide.YES,
        "action": OrderAction.BUY,
        "order_type": OrderType.LIMIT,
        "filled_count": DEFAULT_FINALIZER_FILLED_COUNT,
        "remaining_count": DEFAULT_FINALIZER_REMAINING_COUNT,
        "average_fill_price_cents": DEFAULT_FINALIZER_AVG_PRICE,
        "timestamp": datetime.now(timezone.utc),
        "fees_cents": 4,
        "fills": [],
        "trade_rule": "RULE_ONE",
        "trade_reason": "Valid trade reason",
    }
    base.update(overrides)
    return OrderResponse(**base)


class DummyTradeStore:
    def __init__(self):
        self.records = []

    async def store_trade(self, record):
        self.records.append(record)


class DummyNotifier:
    def __init__(self, *, error: Optional[Exception] = None):
        self.calls = []
        self._error = error

    async def send_order_executed_notification(self, order_data, response_data, kalshi_client):
        self.calls.append((order_data, response_data, kalshi_client))
        if self._error:
            raise self._error


@pytest.mark.asyncio
async def test_trade_finalizer_persists_trade_and_notifies():
    trade_store = DummyTradeStore()
    notifier = DummyNotifier()

    async def provide_store():
        return trade_store

    finalizer = TradeFinalizer(
        trade_store_provider=provide_store,
        context_resolver=lambda ticker: ("weather", "NY"),
        notifier_supplier=lambda: notifier,
        kalshi_client=SimpleNamespace(),
    )

    order_request = _build_order_request()
    order_response = _build_order_response()
    outcome = PollingOutcome(fills=[{"count": 2}], total_filled=2, average_price_cents=45)

    await finalizer.finalize(order_request, order_response, outcome)

    assert trade_store.records
    stored_record = trade_store.records[0]
    assert stored_record.market_ticker == "KXHIGHNYC-25JAN01"
    assert stored_record.quantity == _TEST_COUNT_2
    assert stored_record.market_category == "weather"
    assert stored_record.weather_station == "NY"

    assert notifier.calls
    order_data, response_data, _ = notifier.calls[0]
    assert order_data["count"] == order_response.filled_count + order_response.remaining_count
    assert response_data["filled_count"] == order_response.filled_count


@pytest.mark.asyncio
async def test_trade_finalizer_requires_trade_metadata():
    trade_store = DummyTradeStore()

    async def provide_store():
        return trade_store

    finalizer = TradeFinalizer(
        trade_store_provider=provide_store,
        context_resolver=lambda ticker: ("weather", "NY"),
        notifier_supplier=lambda: None,
        kalshi_client=SimpleNamespace(),
    )

    order_request = _build_order_request()
    order_request.trade_rule = ""
    order_response = _build_order_response()
    outcome = PollingOutcome(fills=[{"count": 1}], total_filled=1, average_price_cents=40)

    with pytest.raises(KalshiTradePersistenceError):
        await finalizer.finalize(order_request, order_response, outcome)


@pytest.mark.asyncio
async def test_trade_finalizer_requires_fees():
    trade_store = DummyTradeStore()

    async def provide_store():
        return trade_store

    finalizer = TradeFinalizer(
        trade_store_provider=provide_store,
        context_resolver=lambda ticker: ("weather", "NY"),
        notifier_supplier=lambda: None,
        kalshi_client=SimpleNamespace(),
    )

    order_request = _build_order_request()
    order_response = _build_order_response()
    order_response.fees_cents = None
    outcome = PollingOutcome(fills=[{"count": 1}], total_filled=1, average_price_cents=40)

    with pytest.raises(KalshiTradePersistenceError):
        await finalizer.finalize(order_request, order_response, outcome)


@pytest.mark.asyncio
async def test_trade_finalizer_wraps_store_errors():
    class FailingTradeStore:
        async def store_trade(self, _record):
            raise RuntimeError("redis down")

    trade_store = FailingTradeStore()

    async def provide_store():
        return trade_store

    finalizer = TradeFinalizer(
        trade_store_provider=provide_store,
        context_resolver=lambda ticker: ("weather", "NY"),
        notifier_supplier=lambda: None,
        kalshi_client=SimpleNamespace(),
    )

    order_request = _build_order_request()
    order_response = _build_order_response()
    outcome = PollingOutcome(fills=[{"count": 1}], total_filled=1, average_price_cents=40)

    with pytest.raises(KalshiTradePersistenceError) as excinfo:
        await finalizer.finalize(order_request, order_response, outcome)

    assert "redis down" in str(excinfo.value)


@pytest.mark.asyncio
async def test_trade_finalizer_wraps_notification_errors():
    trade_store = DummyTradeStore()
    notifier_error = RuntimeError("telegram down")
    notifier = DummyNotifier(error=notifier_error)

    async def provide_store():
        return trade_store

    finalizer = TradeFinalizer(
        trade_store_provider=provide_store,
        context_resolver=lambda ticker: ("weather", "NY"),
        notifier_supplier=lambda: notifier,
        kalshi_client=SimpleNamespace(),
    )

    order_request = _build_order_request()
    order_response = _build_order_response()
    outcome = PollingOutcome(fills=[{"count": 1}], total_filled=1, average_price_cents=40)

    with pytest.raises(KalshiTradeNotificationError) as excinfo:
        await finalizer.finalize(order_request, order_response, outcome)

    assert "telegram down" in str(excinfo.value)
