from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.common.kalshi_trading_client.client_helpers.initialization_coordinator_helpers.service_provider_factory import (
    create_service_providers,
)


async def _gather(result):
    return await result


def test_create_service_providers_returns_callable_mapping():
    trade_store = object()
    manager = SimpleNamespace(get_or_create=AsyncMock(return_value=trade_store))
    private_methods = SimpleNamespace(
        create_order_poller=MagicMock(return_value="poller"),
        create_trade_finalizer=MagicMock(return_value="finalizer"),
    )
    services_holder = {"private_methods": private_methods}

    providers = create_service_providers(manager, services_holder)

    assert set(providers.keys()) == {
        "get_trade_store",
        "get_order_poller",
        "get_trade_finalizer",
    }

    # Invoke provider functions
    trade_store_result = asyncio.run(providers["get_trade_store"]())
    assert trade_store_result is trade_store
    manager.get_or_create.assert_awaited_once()

    assert providers["get_order_poller"]() == "poller"
    assert providers["get_trade_finalizer"]() == "finalizer"


def test_create_service_providers_handles_missing_private_methods():
    manager = MagicMock()
    services_holder = {}

    with patch(
        "src.common.kalshi_trading_client.client_helpers.initialization_coordinator_helpers.service_provider_factory.TradeStoreOperations.get_trade_store",
        AsyncMock(return_value=None),
    ):
        providers = create_service_providers(manager, services_holder)

    assert providers["get_order_poller"]() is None
    assert providers["get_trade_finalizer"]() is None
