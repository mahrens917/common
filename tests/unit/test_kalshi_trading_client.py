import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock

import pytest

from common.data_models.trading import (
    OrderAction,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    PortfolioBalance,
    PortfolioPosition,
)

_CONST_12 = 12
_CONST_45 = 45
_TEST_COUNT_3 = 3
DEFAULT_ORDER_COUNT = 3
DEFAULT_REMAINING_COUNT = 3
ZERO_FILLED_COUNT = 0
DEFAULT_ORDER_REMAINING_COUNT = DEFAULT_REMAINING_COUNT

from common.kalshi_trading_client import KalshiTradingClient
from common.order_execution import PollingOutcome
from common.redis_protocol.trade_store import TradeStoreError
from common.redis_schema.markets import KalshiMarketCategory
from common.trading.notifier_adapter import TradeNotifierAdapter
from common.trading.weather_station import WeatherStationResolver
from common.trading_exceptions import (
    KalshiAPIError,
    KalshiDataIntegrityError,
    KalshiOrderNotFoundError,
    KalshiOrderPollingError,
    KalshiOrderValidationError,
    KalshiTradeNotificationError,
    KalshiTradePersistenceError,
    KalshiTradingError,
)


def _build_order_request(**overrides) -> OrderRequest:
    base = {
        "ticker": "KXHIGHNYC-25JAN01",
        "action": OrderAction.BUY,
        "side": OrderSide.YES,
        "count": DEFAULT_ORDER_COUNT,
        "client_order_id": str(uuid.uuid4()),
        "trade_rule": "rule_3",
        "trade_reason": "Reason long enough",
        "order_type": OrderType.LIMIT,
        "yes_price_cents": 45,
    }
    base.update(overrides)
    return OrderRequest(**base)


def _build_order_response(**overrides) -> OrderResponse:
    base = {
        "order_id": "ORD-123",
        "client_order_id": "CLIENT-1",
        "status": OrderStatus.PENDING,
        "ticker": "KXHIGHNYC-25JAN01",
        "side": OrderSide.YES,
        "action": OrderAction.BUY,
        "order_type": OrderType.LIMIT,
        "filled_count": ZERO_FILLED_COUNT,
        "remaining_count": DEFAULT_REMAINING_COUNT,
        "average_fill_price_cents": None,
        "timestamp": datetime.now(timezone.utc),
        "fees_cents": 0,
        "fills": [],
        "trade_rule": "rule_3",
        "trade_reason": "Reason long enough",
    }
    base.update(overrides)
    return OrderResponse(**base)


def _install_trade_notifier(
    monkeypatch: pytest.MonkeyPatch,
    factory,
    *,
    error_type: type[Exception] = RuntimeError,
    client: Optional[KalshiTradingClient] = None,
) -> None:
    if client is not None:
        client._notifier = TradeNotifierAdapter(
            notifier_supplier=factory,
            notification_error_types=(error_type,),
        )


class DummyPoller:
    def __init__(self, outcome=None, exc: Optional[Exception] = None):
        self.outcome = outcome
        self.exc = exc
        self.calls = []

    async def poll(self, order_id: str, timeout_seconds: float):
        self.calls.append((order_id, timeout_seconds))
        if self.exc:
            raise self.exc
        return self.outcome


def _install_poller(monkeypatch: pytest.MonkeyPatch, client: KalshiTradingClient, **kwargs):
    poller = DummyPoller(**kwargs)
    monkeypatch.setattr(client, "_build_order_poller", lambda: poller)
    return poller


class DummyFinalizer:
    def __init__(self, exc: Optional[Exception] = None):
        self.exc = exc
        self.calls = []

    async def finalize(self, order_request, order_response, outcome):
        self.calls.append((order_request, order_response, outcome))
        if self.exc:
            raise self.exc


def _install_finalizer(
    monkeypatch: pytest.MonkeyPatch,
    client: KalshiTradingClient,
    *,
    exc: Optional[Exception] = None,
):
    finalizer = DummyFinalizer(exc=exc)
    monkeypatch.setattr(client, "_build_trade_finalizer", lambda: finalizer)
    return finalizer


class _StubTradeStore:
    def __init__(self):
        self.metadata: dict[str, dict[str, str]] = {}

    async def initialize(self):
        return True

    async def close(self):
        return None

    async def get_order_metadata(self, order_id: str):
        return self.metadata.get(order_id, {})

    async def store_order_metadata(
        self,
        order_id: str,
        trade_rule: str,
        trade_reason: str,
        *,
        market_category: str | None = None,
        weather_station: str | None = None,
    ) -> bool:
        self.metadata[order_id] = {
            "trade_rule": trade_rule,
            "trade_reason": trade_reason,
        }
        if market_category is not None:
            self.metadata[order_id]["market_category"] = market_category
        if weather_station is not None:
            self.metadata[order_id]["weather_station"] = weather_station
        return True


@pytest.fixture
def bare_trading_client(monkeypatch, config_dict):
    fake_client = SimpleNamespace(attach_trade_store=lambda *_: None)

    monkeypatch.setattr("common.kalshi_trading_client.load_pnl_config", lambda: config_dict)

    resolver = WeatherStationResolver(mapping={})
    trade_store = _StubTradeStore()
    client = KalshiTradingClient(
        kalshi_client=fake_client,
        weather_station_resolver=resolver,
        trade_store=trade_store,
    )
    client.telegram_handler = None
    client.is_running = False
    return client


@pytest.fixture
def config_dict():
    return {
        "trade_collection": {
            "batch_size": 50,
            "collection_interval_seconds": 10,
            "max_retries": 3,
            "retry_delay_seconds": 2,
            "historical_start_date": "2024-01-15",
        },
        "market_filters": {"ticker_pattern": "KXHIGH*", "supported_rules": ["rule_3"]},
    }


@pytest.fixture
def weather_mapping():
    return {
        "NY": {"icao": "KNYC", "aliases": ["NYC"]},
        "DEN": {"icao": "KDEN"},
    }


@pytest.fixture
def configured_client(monkeypatch, config_dict, weather_mapping):
    fake_client = SimpleNamespace(
        initialize=AsyncMock(),
        close=AsyncMock(),
        get_portfolio_balance=AsyncMock(),
        get_portfolio_positions=AsyncMock(),
        create_order=AsyncMock(),
        get_fills=AsyncMock(),
        get_all_fills=AsyncMock(),
        api_request=AsyncMock(),
        get_order=AsyncMock(),
    )
    fake_client.attach_trade_store = lambda *_args, **_kwargs: None

    monkeypatch.setattr("common.kalshi_trading_client.load_pnl_config", lambda: config_dict)

    resolver = WeatherStationResolver(mapping=weather_mapping)
    trade_store = _StubTradeStore()
    client = KalshiTradingClient(
        kalshi_client=fake_client,
        weather_station_resolver=resolver,
        trade_store=trade_store,
    )
    return client, fake_client


def test_init_configures_attributes(configured_client, config_dict, weather_mapping):
    client, _ = configured_client
    assert client.batch_size == config_dict["trade_collection"]["batch_size"]
    assert client.supported_rules == config_dict["market_filters"]["supported_rules"]
    assert client.icao_to_city_mapping == {
        info["icao"]: city for city, info in weather_mapping.items()
    }


def test_init_requires_trade_store(monkeypatch, config_dict):
    fake_client = SimpleNamespace(attach_trade_store=lambda *_args, **_kwargs: None)
    monkeypatch.setattr("common.kalshi_trading_client.load_pnl_config", lambda: config_dict)
    resolver = WeatherStationResolver(mapping={})

    with pytest.raises(ValueError):
        KalshiTradingClient(kalshi_client=fake_client, weather_station_resolver=resolver)


def test_resolve_trade_context_handles_city_alias(monkeypatch, config_dict):
    fake_client = SimpleNamespace(attach_trade_store=lambda *_args, **_kwargs: None)
    mapping = {"NY": {"icao": "KNYC", "aliases": ["NYC", "NEWYORK"]}}

    monkeypatch.setattr("common.kalshi_trading_client.load_pnl_config", lambda: config_dict)

    resolver = WeatherStationResolver(mapping=mapping)
    client = KalshiTradingClient(
        kalshi_client=fake_client,
        weather_station_resolver=resolver,
        trade_store=_StubTradeStore(),
    )

    category, station = client._resolve_trade_context("KXHIGHNYC-25JAN01-B80")

    assert category == KalshiMarketCategory.WEATHER
    assert station == "KNYC"


@pytest.mark.asyncio
async def test_initialize_invokes_client(configured_client):
    client, fake = configured_client
    await client.initialize()
    fake.initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_handles_errors(configured_client):
    client, fake = configured_client
    fake.close.side_effect = RuntimeError("boom")
    await client.close()
    fake.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_context_manager_calls_initialize_and_close(configured_client):
    client, fake = configured_client
    async with client as ctx:
        assert ctx is client
    fake.initialize.assert_awaited_once()
    fake.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_context_manager_propagates_exception(configured_client):
    client, fake = configured_client

    class CustomError(Exception):
        pass

    with pytest.raises(CustomError):
        async with client:
            raise CustomError()

    fake.close.assert_awaited_once()


def test_validate_order_request_accepts_valid_input(bare_trading_client):
    request = _build_order_request()
    bare_trading_client._validate_order_request(request)


def test_validate_order_request_rejects_short_ticker(bare_trading_client):
    request = _build_order_request(ticker="AB")
    with pytest.raises(KalshiOrderValidationError):
        bare_trading_client._validate_order_request(request)


def test_validate_order_request_rejects_non_uuid_client_id(bare_trading_client):
    request = _build_order_request(client_order_id="not-uuid")
    with pytest.raises(KalshiOrderValidationError):
        bare_trading_client._validate_order_request(request)


def test_extract_weather_station_from_alias_maps_known_city(bare_trading_client):
    bare_trading_client.weather_station_mapping = {"AUS": {"icao": "KAUS"}}
    assert (
        bare_trading_client._extract_weather_station_from_ticker("KXHIGHAUS-25AUG15-B80") == "KAUS"
    )


def test_extract_weather_station_from_alias_falls_back_to_mapping_alias(bare_trading_client):
    bare_trading_client.weather_station_mapping = {"NY": {"icao": "KNYC", "aliases": ["NYC"]}}
    assert (
        bare_trading_client._extract_weather_station_from_ticker("KXHIGHNYC-25AUG15-B80") == "KNYC"
    )


@pytest.mark.parametrize(
    ("ticker", "message"),
    [
        ("INVALID-25AUG15", "Market ticker must start with KXHIGH"),
        ("KXHIGHXYZ-25AUG15", "Weather station 'XYZ' not found"),
        ("KXHIGHBAD", "Invalid market ticker format"),
    ],
)
def test_extract_weather_station_errors(bare_trading_client, ticker, message):
    with pytest.raises(ValueError) as exc:
        bare_trading_client._extract_weather_station_from_ticker(ticker)
    assert message in str(exc.value)


def test_create_icao_to_city_mapping_builds_reverse_lookup(bare_trading_client):
    bare_trading_client.weather_station_mapping = {
        "AUS": {"icao": "KAUS"},
        "DEN": {"icao": "KDEN"},
        "MISSING": {},
    }
    assert bare_trading_client._create_icao_to_city_mapping() == {
        "KAUS": "AUS",
        "KDEN": "DEN",
    }


@pytest.mark.asyncio
async def test_calculate_order_fees_uses_fee_helper(monkeypatch, bare_trading_client):
    def fake_calculate(quantity, price_cents, ticker):
        assert quantity == _TEST_COUNT_3
        assert price_cents == _CONST_45
        assert ticker == "KXHIGHNYC-25JAN01"
        return 12

    monkeypatch.setattr("common.kalshi_trading_client.calculate_fees", fake_calculate)
    fee = await bare_trading_client._calculate_order_fees("KXHIGHNYC-25JAN01", 3, 45)
    assert fee == _CONST_12


@pytest.mark.asyncio
async def test_calculate_order_fees_propagates_error(monkeypatch, bare_trading_client):
    monkeypatch.setattr(
        "common.kalshi_trading_client.calculate_fees",
        lambda *_: (_ for _ in ()).throw(RuntimeError("fail")),
    )

    with pytest.raises(ValueError):
        await bare_trading_client._calculate_order_fees("KXHIGHNYC-25JAN01", 1, 20)


def test_has_sufficient_balance_for_trade_with_fees(bare_trading_client):
    assert bare_trading_client.has_sufficient_balance_for_trade_with_fees(1000, 800, 100)
    assert not bare_trading_client.has_sufficient_balance_for_trade_with_fees(500, 400, 200)


def test_parse_order_response_with_wrapped_payload(monkeypatch, bare_trading_client):
    response_data = {"order": {"id": "123"}}
    parsed = _build_order_response()

    def fake_validate(data):
        assert data is response_data
        return {"parsed": True}

    def fake_parse(data, trade_rule, trade_reason):
        assert data == {"parsed": True}
        assert trade_rule == "rule-x"
        assert trade_reason == "Reason long enough"
        return parsed

    monkeypatch.setattr(
        "common.order_response_parser.validate_order_response_schema", fake_validate
    )
    monkeypatch.setattr("common.order_response_parser.parse_kalshi_order_response", fake_parse)

    result = bare_trading_client._parse_order_response(
        response_data, operation_name="op", trade_rule="rule-x", trade_reason="Reason long enough"
    )
    assert result is parsed


def test_parse_order_response_without_wrapper(monkeypatch, bare_trading_client):
    response_data = {"id": "123"}
    parsed = _build_order_response()

    def fail_validate(_):
        raise AssertionError("validate should not run")

    def fake_parse(data, trade_rule, trade_reason):
        assert data is response_data
        return parsed

    monkeypatch.setattr(
        "common.order_response_parser.validate_order_response_schema", fail_validate
    )
    monkeypatch.setattr("common.order_response_parser.parse_kalshi_order_response", fake_parse)

    result = bare_trading_client._parse_order_response(
        response_data, operation_name="op", trade_rule="rule-x", trade_reason="Reason long enough"
    )
    assert result is parsed


def test_parse_order_response_converts_value_error(monkeypatch, bare_trading_client):
    def fake_validate(data):
        return data["order"]

    monkeypatch.setattr(
        "common.order_response_parser.validate_order_response_schema", fake_validate
    )
    monkeypatch.setattr(
        "common.order_response_parser.parse_kalshi_order_response",
        lambda *_: (_ for _ in ()).throw(ValueError("bad")),
    )

    with pytest.raises(KalshiDataIntegrityError) as exc:
        bare_trading_client._parse_order_response(
            {"order": {"id": "1"}},
            operation_name="op",
            trade_rule="rule",
            trade_reason="Reason long enough",
        )
    assert "bad" in str(exc.value)


def test_parse_order_response_wraps_unexpected_errors(monkeypatch, bare_trading_client):
    def fake_validate(data):
        return data["order"]

    monkeypatch.setattr(
        "common.order_response_parser.validate_order_response_schema", fake_validate
    )
    monkeypatch.setattr(
        "common.order_response_parser.parse_kalshi_order_response",
        lambda *_: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(KalshiDataIntegrityError) as exc:
        bare_trading_client._parse_order_response(
            {"order": {"id": "1"}},
            operation_name="op",
            trade_rule="rule",
            trade_reason="Reason long enough",
        )
    assert "boom" in str(exc.value)


def test_parse_order_response_schema_validator_failure(monkeypatch, bare_trading_client):
    monkeypatch.setattr(
        "common.order_response_parser.validate_order_response_schema",
        lambda *_: (_ for _ in ()).throw(ValueError("schema mismatch")),
    )

    with pytest.raises(KalshiDataIntegrityError):
        bare_trading_client._parse_order_response(
            {"order": {"id": "1"}},
            operation_name="op",
            trade_rule="rule",
            trade_reason="Reason long enough",
        )


@pytest.mark.asyncio
async def test_get_portfolio_balance_success(configured_client):
    client, fake = configured_client
    balance = PortfolioBalance(
        balance_cents=1234, currency="USD", timestamp=datetime.now(timezone.utc)
    )
    fake.get_portfolio_balance.return_value = balance

    result = await client.get_portfolio_balance()
    assert result is balance


@pytest.mark.asyncio
async def test_get_portfolio_balance_failure(configured_client):
    client, fake = configured_client
    fake.get_portfolio_balance.side_effect = RuntimeError("down")

    with pytest.raises(KalshiAPIError):
        await client.get_portfolio_balance()


@pytest.mark.asyncio
async def test_get_portfolio_positions_success(configured_client):
    client, fake = configured_client
    position = PortfolioPosition(
        ticker="KXHIGHNYC-25JAN01",
        position_count=5,
        side=OrderSide.YES,
        market_value_cents=500,
        unrealized_pnl_cents=20,
        average_price_cents=10,
        last_updated=datetime.now(timezone.utc),
    )
    fake.get_portfolio_positions.return_value = [position]

    result = await client.get_portfolio_positions()
    assert result == [position]


@pytest.mark.asyncio
async def test_get_portfolio_positions_failure(configured_client):
    client, fake = configured_client
    fake.get_portfolio_positions.side_effect = RuntimeError("down")

    with pytest.raises(KalshiAPIError):
        await client.get_portfolio_positions()


@pytest.mark.asyncio
async def test_create_order_stores_metadata(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(fees_cents=2)
    fake.create_order.return_value = response

    calls = {}

    class DummyTradeStore:
        def __init__(self):
            calls["instance"] = True

        async def initialize(self):
            calls["initialize"] = True
            return True

        async def store_order_metadata(
            self, order_id, trade_rule, trade_reason, *, market_category=None, weather_station=None
        ):
            calls["metadata"] = (
                order_id,
                trade_rule,
                trade_reason,
                market_category,
                weather_station,
            )
            return True

        async def close(self):
            calls["close"] = True

    client.trade_store = DummyTradeStore()
    monkeypatch.setattr(client, "_extract_weather_station_from_ticker", lambda _: "KNYC")
    _install_trade_notifier(monkeypatch, lambda: None, client=client)

    result = await client.create_order(request)
    assert result is response
    assert calls["metadata"][0:3] == (
        response.order_id,
        request.trade_rule,
        request.trade_reason,
    )
    assert calls["metadata"][3] == "weather"
    assert calls["metadata"][4] == "KNYC"


@pytest.mark.asyncio
async def test_create_order_metadata_failure_raises(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response()
    fake.create_order.return_value = response

    class DummyTradeStore:
        async def initialize(self):
            return True

        async def store_order_metadata(self, *_, **__):
            raise TradeStoreError("metadata failure")

        async def close(self):
            pass

    client.trade_store = DummyTradeStore()
    monkeypatch.setattr(client, "_extract_weather_station_from_ticker", lambda _: "KNYC")
    _install_trade_notifier(monkeypatch, lambda: None, client=client)

    with pytest.raises(KalshiTradePersistenceError, match="metadata failure"):
        await client.create_order(request)


@pytest.mark.asyncio
async def test_create_order_handles_trading_error(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    fake.create_order.side_effect = KalshiTradingError("insufficient funds")

    class DummyNotifier:
        def __init__(self):
            self.called = False

        async def send_order_error_notification(self, order_data, err):
            self.called = True
            raise RuntimeError("notify fail")

    notifier = DummyNotifier()
    _install_trade_notifier(monkeypatch, lambda: notifier, client=client)

    with pytest.raises(KalshiTradeNotificationError):
        await client.create_order(request)

    assert notifier.called


@pytest.mark.asyncio
async def test_create_order_handles_trading_error_notifier_specific(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    fake.create_order.side_effect = KalshiTradingError("insufficient funds")

    class CustomTradeNotificationError(Exception):
        pass

    class DummyNotifier:
        def __init__(self):
            self.called = False

        async def send_order_error_notification(self, order_data, err):
            self.called = True
            raise CustomTradeNotificationError("notify fail")

    notifier = DummyNotifier()
    _install_trade_notifier(
        monkeypatch,
        lambda: notifier,
        error_type=CustomTradeNotificationError,
        client=client,
    )

    with pytest.raises(KalshiTradeNotificationError) as excinfo:
        await client.create_order(request)

    assert notifier.called
    assert "Failed to publish trading error notification" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_order_handles_unexpected_error(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    fake.create_order.side_effect = RuntimeError("api down")

    class DummyNotifier:
        def __init__(self):
            self.called = False

        async def send_order_error_notification(self, order_data, err):
            self.called = True
            raise RuntimeError("notify fail")

    notifier = DummyNotifier()
    _install_trade_notifier(monkeypatch, lambda: notifier, client=client)

    with pytest.raises(KalshiTradeNotificationError):
        await client.create_order(request)

    assert notifier.called


@pytest.mark.asyncio
async def test_create_order_handles_unexpected_error_notifier_specific(
    monkeypatch, configured_client
):
    client, fake = configured_client
    request = _build_order_request()
    fake.create_order.side_effect = RuntimeError("api down")

    class CustomTradeNotificationError(Exception):
        pass

    class DummyNotifier:
        def __init__(self):
            self.called = False

        async def send_order_error_notification(self, order_data, err):
            self.called = True
            raise CustomTradeNotificationError("notify fail")

    notifier = DummyNotifier()
    _install_trade_notifier(
        monkeypatch,
        lambda: notifier,
        error_type=CustomTradeNotificationError,
        client=client,
    )

    with pytest.raises(KalshiTradeNotificationError) as excinfo:
        await client.create_order(request)

    assert notifier.called
    assert "Failed to publish unexpected error notification" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_order_with_polling_immediate_fill(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(
        filled_count=DEFAULT_ORDER_COUNT, remaining_count=DEFAULT_ORDER_REMAINING_COUNT
    )
    client.create_order = AsyncMock(return_value=response)

    def fail_poller():
        raise AssertionError("poller should not be built for immediate fills")

    monkeypatch.setattr(client, "_build_order_poller", fail_poller)

    result = await client.create_order_with_polling(request, timeout_seconds=1)
    assert result is response


@pytest.mark.asyncio
async def test_create_order_with_polling_immediate_cancel(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(status=OrderStatus.CANCELLED)
    client.create_order = AsyncMock(return_value=response)

    def fail_poller():
        raise AssertionError("poller should not be built for cancelled orders")

    monkeypatch.setattr(client, "_build_order_poller", fail_poller)

    result = await client.create_order_with_polling(request, timeout_seconds=1)
    assert result is response


@pytest.mark.asyncio
async def test_create_order_with_polling_processes_fills(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(fees_cents=6)
    client.create_order = AsyncMock(return_value=response)
    polling_outcome = PollingOutcome(
        fills=[{"count": 2}, {"count": 1}],
        total_filled=3,
        average_price_cents=35,
    )
    poller = _install_poller(monkeypatch, client, outcome=polling_outcome)
    finalizer = _install_finalizer(monkeypatch, client)

    result = await client.create_order_with_polling(request, timeout_seconds=1)
    assert result.status == OrderStatus.FILLED
    assert result.filled_count == _TEST_COUNT_3
    assert result.remaining_count == 0
    assert finalizer.calls
    called_request, called_response, called_outcome = finalizer.calls[0]
    assert called_request is request
    assert called_response is response
    assert called_outcome is polling_outcome
    assert poller.calls == [(response.order_id, 1)]


@pytest.mark.asyncio
async def test_create_order_with_polling_allows_non_weather_trade(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request(
        ticker="KXBTCJAN25-100",
        trade_rule="EMERGENCY_EXIT",
        trade_reason="Emergency exit rule",
    )
    response = _build_order_response(
        fees_cents=4,
        ticker="KXBTCJAN25-100",
        trade_rule="EMERGENCY_EXIT",
        trade_reason="Emergency exit rule",
    )
    client.create_order = AsyncMock(return_value=response)
    polling_outcome = PollingOutcome(fills=[{"count": 2}], total_filled=2, average_price_cents=60)
    _install_poller(monkeypatch, client, outcome=polling_outcome)
    finalizer = _install_finalizer(monkeypatch, client)

    result = await client.create_order_with_polling(request, timeout_seconds=1)
    assert result.status == OrderStatus.FILLED
    assert finalizer.calls
    assert finalizer.calls[0][0].ticker == "KXBTCJAN25-100"


@pytest.mark.asyncio
async def test_create_order_with_polling_handles_empty_fills(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(fees_cents=1)
    client.create_order = AsyncMock(return_value=response)
    _install_poller(monkeypatch, client, outcome=None)
    finalizer = _install_finalizer(monkeypatch, client, exc=AssertionError("should not finalize"))
    client.cancel_order = AsyncMock(return_value=True)
    cancelled = _build_order_response(
        status=OrderStatus.CANCELLED,
        remaining_count=response.remaining_count,
        filled_count=response.filled_count,
        fees_cents=response.fees_cents,
        average_fill_price_cents=response.average_fill_price_cents,
    )
    fake.get_order = AsyncMock(return_value=cancelled)

    result = await client.create_order_with_polling(request, timeout_seconds=1)
    assert result is cancelled
    assert result.status == OrderStatus.CANCELLED
    assert not finalizer.calls
    client.cancel_order.assert_awaited_once_with(response.order_id)
    fake.get_order.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_order_with_polling_trade_store_failure(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(fees_cents=2)
    client.create_order = AsyncMock(return_value=response)
    polling_outcome = PollingOutcome(fills=[{"count": 1}], total_filled=1, average_price_cents=50)
    _install_poller(monkeypatch, client, outcome=polling_outcome)
    failure = KalshiTradePersistenceError(
        "store fail", order_id=response.order_id, ticker=response.ticker
    )
    _install_finalizer(monkeypatch, client, exc=failure)

    with pytest.raises(KalshiTradePersistenceError):
        await client.create_order_with_polling(request, timeout_seconds=1)


@pytest.mark.asyncio
async def test_create_order_with_polling_missing_metadata(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(fees_cents=2)
    client.create_order = AsyncMock(return_value=response)
    polling_outcome = PollingOutcome(fills=[{"count": 1}], total_filled=1, average_price_cents=40)
    _install_poller(monkeypatch, client, outcome=polling_outcome)
    failure = KalshiTradePersistenceError(
        "missing metadata", order_id=response.order_id, ticker=response.ticker
    )
    _install_finalizer(monkeypatch, client, exc=failure)

    with pytest.raises(KalshiTradePersistenceError):
        await client.create_order_with_polling(request, timeout_seconds=1)


@pytest.mark.asyncio
async def test_create_order_with_polling_notifier_failure(monkeypatch, configured_client, caplog):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(fees_cents=2)
    client.create_order = AsyncMock(return_value=response)
    polling_outcome = PollingOutcome(fills=[{"count": 1}], total_filled=1, average_price_cents=50)
    _install_poller(monkeypatch, client, outcome=polling_outcome)
    failure = KalshiTradeNotificationError("notify fail", order_id=response.order_id)
    _install_finalizer(monkeypatch, client, exc=failure)
    caplog.set_level("ERROR")

    with pytest.raises(KalshiTradeNotificationError):
        await client.create_order_with_polling(request, timeout_seconds=1)


@pytest.mark.asyncio
async def test_create_order_with_polling_fill_lookup_error(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(fees_cents=2)
    client.create_order = AsyncMock(return_value=response)
    _install_finalizer(monkeypatch, client)
    poll_error = KalshiOrderPollingError(
        "api fail",
        order_id=response.order_id,
        operation_name="create_order_with_polling",
    )
    _install_poller(monkeypatch, client, exc=poll_error)

    with pytest.raises(KalshiOrderPollingError):
        await client.create_order_with_polling(request, timeout_seconds=1)


@pytest.mark.asyncio
async def test_create_order_with_polling_zero_total_fill(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(fees_cents=1)
    client.create_order = AsyncMock(return_value=response)
    _install_finalizer(monkeypatch, client)
    poll_error = KalshiOrderPollingError(
        "zero total",
        order_id=response.order_id,
        operation_name="create_order_with_polling",
    )
    _install_poller(monkeypatch, client, exc=poll_error)

    with pytest.raises(KalshiOrderPollingError):
        await client.create_order_with_polling(request, timeout_seconds=1)


@pytest.mark.asyncio
async def test_create_order_with_polling_missing_trade_reason(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response(fees_cents=1)
    client.create_order = AsyncMock(return_value=response)
    polling_outcome = PollingOutcome(fills=[{"count": 1}], total_filled=1, average_price_cents=40)
    _install_poller(monkeypatch, client, outcome=polling_outcome)
    failure = KalshiTradePersistenceError(
        "missing reason", order_id=response.order_id, ticker=response.ticker
    )
    _install_finalizer(monkeypatch, client, exc=failure)

    with pytest.raises(KalshiTradePersistenceError):
        await client.create_order_with_polling(request, timeout_seconds=1)


@pytest.mark.asyncio
async def test_create_order_with_polling_missing_fees(monkeypatch, configured_client):
    client, fake = configured_client
    request = _build_order_request()
    response = _build_order_response()
    response.fees_cents = None
    client.create_order = AsyncMock(return_value=response)
    polling_outcome = PollingOutcome(fills=[{"count": 1}], total_filled=1, average_price_cents=40)
    _install_poller(monkeypatch, client, outcome=polling_outcome)
    failure = KalshiTradePersistenceError(
        "missing fees", order_id=response.order_id, ticker=response.ticker
    )
    _install_finalizer(monkeypatch, client, exc=failure)

    with pytest.raises(KalshiTradePersistenceError):
        await client.create_order_with_polling(request, timeout_seconds=1)


@pytest.mark.asyncio
async def test_cancel_order_success(monkeypatch, configured_client):
    client, fake = configured_client
    fake.api_request.return_value = {"status": "cancelled"}
    monkeypatch.setattr(
        "common.api_response_validators.validate_cancel_order_response",
        lambda data: data,
    )

    assert await client.cancel_order("ORD-1") is True


@pytest.mark.asyncio
async def test_cancel_order_returns_false_for_other_status(monkeypatch, configured_client):
    client, fake = configured_client
    fake.api_request.return_value = {"status": "pending"}
    monkeypatch.setattr(
        "common.api_response_validators.validate_cancel_order_response",
        lambda data: data,
    )

    assert await client.cancel_order("ORD-2") is False


@pytest.mark.asyncio
async def test_cancel_order_validation_error_still_allows_success(monkeypatch, configured_client):
    client, fake = configured_client
    fake.api_request.return_value = {"order": {"status": "canceled"}}

    def fake_validate(_):
        raise ValueError("schema mismatch")

    monkeypatch.setattr(
        "common.api_response_validators.validate_cancel_order_response",
        fake_validate,
    )

    with pytest.raises(KalshiAPIError):
        await client.cancel_order("ORD-3")


@pytest.mark.asyncio
async def test_cancel_order_validation_failure_raises_api_error(monkeypatch, configured_client):
    client, fake = configured_client
    fake.api_request.return_value = {"order": {"status": "unknown"}}

    def fake_validate(_):
        raise ValueError("bad")

    monkeypatch.setattr(
        "common.api_response_validators.validate_cancel_order_response",
        fake_validate,
    )

    with pytest.raises(KalshiAPIError):
        await client.cancel_order("ORD-4")


@pytest.mark.asyncio
async def test_cancel_order_not_found(configured_client):
    client, fake = configured_client
    fake.api_request.side_effect = RuntimeError("Not Found")

    with pytest.raises(KalshiOrderNotFoundError):
        await client.cancel_order("ORD-5")


@pytest.mark.asyncio
async def test_cancel_order_generic_failure(configured_client):
    client, fake = configured_client
    fake.api_request.side_effect = RuntimeError("rate limit")

    with pytest.raises(KalshiAPIError):
        await client.cancel_order("ORD-6")


@pytest.mark.asyncio
async def test_get_fills_success(configured_client):
    client, fake = configured_client
    fake.get_fills.return_value = [{"id": "1"}]
    assert await client.get_fills("ORD-1") == [{"id": "1"}]


@pytest.mark.asyncio
async def test_get_fills_failure(configured_client):
    client, fake = configured_client
    fake.get_fills.side_effect = RuntimeError("fail")

    with pytest.raises(KalshiAPIError):
        await client.get_fills("ORD-1")


@pytest.mark.asyncio
async def test_get_all_fills_success(configured_client):
    client, fake = configured_client
    fake.get_all_fills.return_value = {"fills": []}
    assert await client.get_all_fills(ticker="KXHIGHNYC-25JAN01") == {"fills": []}


@pytest.mark.asyncio
async def test_get_all_fills_failure(configured_client):
    client, fake = configured_client
    fake.get_all_fills.side_effect = RuntimeError("fail")

    with pytest.raises(KalshiAPIError):
        await client.get_all_fills()


@pytest.mark.asyncio
async def test_start_trade_collection_requires_trade_store(bare_trading_client):
    async def missing_store():
        raise RuntimeError("no store")

    bare_trading_client._get_trade_store = missing_store

    with pytest.raises(ValueError):
        await bare_trading_client.start_trade_collection()


@pytest.mark.asyncio
async def test_start_trade_collection_sets_flag(bare_trading_client):
    class DummyStore:
        async def initialize(self):
            pass

    bare_trading_client.trade_store = DummyStore()
    await bare_trading_client.start_trade_collection()
    assert bare_trading_client.is_running is True


@pytest.mark.asyncio
async def test_stop_trade_collection_clears_flag(bare_trading_client):
    bare_trading_client.is_running = True
    await bare_trading_client.stop_trade_collection()
    assert bare_trading_client.is_running is False


@pytest.mark.asyncio
async def test_get_trade_metadata_from_order_returns_metadata(monkeypatch, bare_trading_client):
    class DummyStore:
        async def initialize(self):
            pass

        async def get_order_metadata(self, order_id):
            assert order_id == "ORD-1"
            return {"trade_rule": "rule_3", "trade_reason": "Reason long enough"}

    bare_trading_client.trade_store = DummyStore()

    reason, rule = await bare_trading_client._get_trade_metadata_from_order("ORD-1")
    assert (reason, rule) == ("Reason long enough", "rule_3")


@pytest.mark.asyncio
async def test_get_trade_metadata_from_order_missing(monkeypatch, bare_trading_client):
    class DummyStore:
        async def initialize(self):
            pass

        async def get_order_metadata(self, _):
            return None

    bare_trading_client.trade_store = DummyStore()

    with pytest.raises(KalshiDataIntegrityError):
        await bare_trading_client._get_trade_metadata_from_order("ORD-2")


@pytest.mark.asyncio
async def test_get_trade_metadata_from_order_alerts_on_failure(monkeypatch, bare_trading_client):
    class DummyStore:
        async def initialize(self):
            pass

        async def get_order_metadata(self, _):
            raise RuntimeError("redis down")

    class DummyTelegram:
        def __init__(self):
            self.sent = False

        async def send_alert(self, message):
            self.sent = True
            assert "ORD-3" in message

    bare_trading_client.telegram_handler = DummyTelegram()
    bare_trading_client.trade_store = DummyStore()

    with pytest.raises(KalshiDataIntegrityError):
        await bare_trading_client._get_trade_metadata_from_order("ORD-3")

    assert bare_trading_client.telegram_handler.sent


@pytest.mark.asyncio
async def test_get_trade_metadata_from_order_alerts_on_failure_handles_alert_error(
    monkeypatch, bare_trading_client, caplog
):
    class DummyStore:
        async def initialize(self):
            pass

        async def get_order_metadata(self, _):
            raise RuntimeError("redis down")

    class FailingTelegram:
        async def send_alert(self, _):
            raise RuntimeError("telegram fail")

    bare_trading_client.telegram_handler = FailingTelegram()
    bare_trading_client.trade_store = DummyStore()
    caplog.set_level("ERROR")

    with pytest.raises(KalshiDataIntegrityError):
        await bare_trading_client._get_trade_metadata_from_order("ORD-FAIL")

    assert "Failed to send telegram alert" in caplog.text


@pytest.mark.asyncio
async def test_get_trade_metadata_from_order_short_reason(monkeypatch, bare_trading_client):
    class DummyStore:
        async def initialize(self):
            pass

        async def get_order_metadata(self, _):
            return {"trade_rule": "rule_3", "trade_reason": "short"}

    class DummyTelegram:
        async def send_alert(self, _):
            pass

    bare_trading_client.telegram_handler = DummyTelegram()
    bare_trading_client.trade_store = DummyStore()

    with pytest.raises(KalshiDataIntegrityError):
        await bare_trading_client._get_trade_metadata_from_order("ORD-4")


@pytest.mark.asyncio
async def test_get_trade_metadata_from_order_reraises_data_integrity(
    monkeypatch, bare_trading_client
):
    original_error = KalshiDataIntegrityError("historic")

    class DummyStore:
        async def initialize(self):
            pass

        async def get_order_metadata(self, _):
            raise original_error

    bare_trading_client.trade_store = DummyStore()

    with pytest.raises(KalshiDataIntegrityError) as exc:
        await bare_trading_client._get_trade_metadata_from_order("ORD-5")

    assert exc.value is original_error
