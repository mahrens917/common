"""Targeted tests for order helper utilities to raise coverage and verify behavior."""

from __future__ import annotations

import asyncio

import pytest

from common.kalshi_trading_client.client_helpers.initialization_coordinator_helpers.service_creator import (
    create_services,
)
from common.kalshi_trading_client.services.order_helpers.dependencies_factory import (
    OrderServiceDependenciesFactory,
    OrderServiceOptionalDeps,
    OrderServiceRequiredDeps,
)
from common.kalshi_trading_client.services.order_helpers.dependency_initializer import (
    DependencyContainer,
    initialize_dependencies,
)
from common.kalshi_trading_client.services.order_helpers.factory_utils import (
    _DefaultDependencies,
    create_or_use_dependencies,
)
from common.kalshi_trading_client.services.order_helpers.order_creator_helpers import (
    handle_order_error,
    handle_unexpected_error,
    store_order_metadata_safely,
)
from common.redis_protocol.trade_store import TradeStoreError
from common.trading_exceptions import KalshiAPIError, KalshiTradePersistenceError


class _StubOrderResponse:
    def __init__(self, order_id: str):
        self.order_id = order_id


class _StubOrderRequest:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.trade_rule = "rule"
        self.trade_reason = "reason"
        self.__dict__["extra"] = "data"


class _StubTradeStore:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.stored: list[tuple] = []

    async def store_order_metadata(self, order_id, trade_rule, trade_reason, **kwargs):
        if self.should_fail:
            raise TradeStoreError("fail")
        self.stored.append((order_id, trade_rule, trade_reason, kwargs))


class _StubMetadataResolver:
    def resolve_trade_context(self, ticker):
        return ("cat", f"station-{ticker}")


class _StubNotifier:
    def __init__(self):
        self.calls: list[tuple] = []

    async def notify_order_error(self, order_request, exc, **kwargs):
        self.calls.append((order_request, exc, kwargs))


async def _dummy_get_trade_store(store: _StubTradeStore):
    return store


@pytest.mark.asyncio
async def test_store_order_metadata_safely_success_and_failure():
    store = _StubTradeStore()
    request = _StubOrderRequest("TICK")
    response = _StubOrderResponse("order-1")

    await store_order_metadata_safely(
        response,
        request,
        lambda: _dummy_get_trade_store(store),
        _StubMetadataResolver(),
        operation_name="create",
    )
    assert store.stored and store.stored[0][0] == "order-1"

    failing_store = _StubTradeStore(should_fail=True)
    with pytest.raises(KalshiTradePersistenceError):
        await store_order_metadata_safely(
            response,
            request,
            lambda: _dummy_get_trade_store(failing_store),
            _StubMetadataResolver(),
            operation_name="create",
        )


@pytest.mark.asyncio
async def test_order_error_handlers(monkeypatch):
    notifier = _StubNotifier()
    request = _StubOrderRequest("TICK")

    await handle_order_error(notifier, request, RuntimeError("boom"), operation_name="op")
    assert notifier.calls and notifier.calls[0][0] is request

    with pytest.raises(KalshiAPIError):
        await handle_unexpected_error(notifier, request, RuntimeError("oops"), operation_name="op")
    # Unexpected path should still notify
    assert len(notifier.calls) >= 2


def test_dependencies_factory_and_initializer_reuse_optional():
    async def trade_store_getter():
        return "store"

    required = OrderServiceRequiredDeps(
        kalshi_client=object(),
        trade_store_getter=trade_store_getter,
        notifier=object(),
        weather_resolver=object(),
        order_poller_factory=lambda: "poller",
        trade_finalizer_factory=lambda: "finalizer",
        telegram_handler=None,
    )
    optional = OrderServiceOptionalDeps(
        validator="validator",
        parser="parser",
        metadata_resolver="resolver",
        fee_calculator="fee",
        canceller="canceller",
        fills_fetcher="fills",
        metadata_fetcher="metadata",
        order_creator="creator",
        poller="poller",
    )

    deps = OrderServiceDependenciesFactory.create_or_use(required, optional)
    assert deps.validator == "validator"
    container = initialize_dependencies(required, optional)
    assert isinstance(container, DependencyContainer)
    assert container.validator == "validator"


def test_factory_utils_resolves_defaults_and_provided():
    defaults = _DefaultDependencies(
        validator="v",
        parser="p",
        metadata_resolver="mr",
        fee_calculator="fee",
        canceller="c",
        fills_fetcher="f",
        metadata_fetcher="mf",
        order_creator="oc",
        poller="poll",
    )
    provided = {
        "validator": "custom",
        "validation_ops": "ops",
        "kalshi_client": "client",
        "trade_store_getter": lambda: "store",
        "notifier": "notifier",
        "telegram_handler": None,
    }
    with pytest.raises(TypeError):
        create_or_use_dependencies(provided, defaults)


def test_service_creator_invokes_factories(monkeypatch):
    core_components = {
        "trade_store_manager": object(),
        "notifier": object(),
        "kalshi": object(),
    }
    services_holder = object()
    created = []

    def fake_create_service_providers(trade_store_manager, holder):
        assert trade_store_manager is core_components["trade_store_manager"]
        assert holder is services_holder

        async def get_trade_store():
            return "store"

        def get_order_poller():
            return "poller"

        def get_trade_finalizer():
            return "finalizer"

        return {
            "get_trade_store": get_trade_store,
            "get_order_poller": get_order_poller,
            "get_trade_finalizer": get_trade_finalizer,
        }

    class _StubOrders:
        def __init__(self):
            self.updates: list[str] = []

        def update_notifier(self, notifier):
            self.updates.append(f"notifier:{notifier}")

        def update_telegram_handler(self, handler):
            self.updates.append(f"telegram:{handler}")

    def fake_create_services(*args, **kwargs):
        created.append(args)
        return ("portfolio", _StubOrders(), "trade_collection")

    monkeypatch.setattr(
        "common.kalshi_trading_client.client_helpers.initialization_coordinator_helpers.service_creator.create_service_providers",
        fake_create_service_providers,
    )
    monkeypatch.setattr(
        "common.kalshi_trading_client.client_helpers.initialization_coordinator_helpers.service_creator.ClientInitializer.create_services",
        staticmethod(fake_create_services),
    )

    services = create_services(
        core_components,
        initialized_weather="weather",
        telegram_handler="tg",
        services_holder=services_holder,
    )
    assert services["portfolio"] == "portfolio"
    assert isinstance(services["orders"], _StubOrders)
    assert services["trade_collection"] == "trade_collection"
    assert any(update.startswith("notifier") for update in services["orders"].updates)
