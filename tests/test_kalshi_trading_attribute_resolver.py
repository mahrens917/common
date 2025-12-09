import pytest

from src.common.kalshi_trading_client.client_helpers.attribute_resolver import (
    ClientAttributeResolver,
)


class _FakeAPI:
    def __init__(self):
        self.calls = {"start": 0, "stop": 0, "require": 0}

    async def start_trade_collection(self):
        self.calls["start"] += 1
        return True

    async def stop_trade_collection(self):
        self.calls["stop"] += 1
        return False

    async def require_trade_store(self):
        self.calls["require"] += 1
        return "trade-store"

    async def ping(self):
        return "pong"


class _FakeDelegator:
    def __init__(self):
        self.invocations = []

    def foo(self):
        self.invocations.append("foo")
        return "bar"

    def has_sufficient_balance_for_trade_with_fees(self, value):
        self.invocations.append(("balance", value))
        return value > 0


class _FakeTradeStoreManager:
    def __init__(self):
        self.calls = []

    async def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        return "store"

    async def maybe_get(self, **kwargs):
        self.calls.append(("maybe_get", kwargs))

    async def ensure(self, **kwargs):
        self.calls.append(("ensure", kwargs))
        return "ensured-store"


class _FakeClient:
    def __init__(self):
        self._api = _FakeAPI()
        self._delegator = _FakeDelegator()
        self._trade_store_manager = _FakeTradeStoreManager()
        self.is_running = False
        self.trade_store = None

    async def _get_trade_store(self):
        return "store"


@pytest.mark.asyncio
async def test_resolver_wraps_start_and_stop_updates_state():
    client = _FakeClient()
    resolver = ClientAttributeResolver(client)

    start = resolver.resolve("start_trade_collection")
    await start()
    assert client.is_running is True

    stop = resolver.resolve("stop_trade_collection")
    await stop()
    assert client.is_running is False


@pytest.mark.asyncio
async def test_resolver_wraps_require_trade_store_updates_client():
    client = _FakeClient()
    resolver = ClientAttributeResolver(client)

    require = resolver.resolve("require_trade_store")
    result = await require()

    assert result == "trade-store"
    assert client.trade_store == "trade-store"


def test_resolver_delegates_private_methods_and_balance_check():
    client = _FakeClient()
    resolver = ClientAttributeResolver(client)

    foo = resolver.resolve("_foo")
    assert foo() == "bar"

    balance_check = resolver.resolve("has_sufficient_balance_for_trade_with_fees")
    assert balance_check(10) is True
    assert balance_check(-1) is False

    assert client._delegator.invocations[0] == "foo"
    assert client._delegator.invocations[1] == ("balance", 10)


def test_resolver_raises_for_missing_attribute():
    client = _FakeClient()
    resolver = ClientAttributeResolver(client)

    with pytest.raises(AttributeError):
        resolver.resolve("unknown_method")
