from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.common.trading.trade_store_manager import TradeStoreManager


class _ExternalStore:
    def __init__(self) -> None:
        self.initialized = 0

    async def initialize(self) -> None:
        self.initialized += 1


class _ManagedStore:
    def __init__(self) -> None:
        self.initialized = False
        self.closed = False

    async def initialize(self) -> None:
        self.initialized = True

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_ensure_uses_external_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _ExternalStore()
    attached = []
    client = SimpleNamespace(attach_trade_store=lambda s: attached.append(s))
    manager = TradeStoreManager(kalshi_client=client, store_supplier=lambda: store)

    result = await manager.ensure(create=True)

    assert result is store
    assert store.initialized == 1
    assert attached == [store]


@pytest.mark.asyncio
async def test_get_or_create_builds_managed_store(monkeypatch: pytest.MonkeyPatch) -> None:
    attached = []
    client = SimpleNamespace(attach_trade_store=lambda s: attached.append(s))
    manager = TradeStoreManager(kalshi_client=client, store_supplier=lambda: None)

    monkeypatch.setattr("src.common.redis_protocol.trade_store.TradeStore", _ManagedStore)

    store = await manager.get_or_create()

    assert isinstance(store, _ManagedStore)
    assert store.initialized is True
    assert attached == [store]


@pytest.mark.asyncio
async def test_close_managed_store(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SimpleNamespace(attach_trade_store=lambda *_: None)
    manager = TradeStoreManager(kalshi_client=client, store_supplier=lambda: None)
    monkeypatch.setattr("src.common.redis_protocol.trade_store.TradeStore", _ManagedStore)

    store = await manager.get_or_create()
    await manager.close_managed()

    assert store.closed is True


@pytest.mark.asyncio
async def test_maybe_get_without_store() -> None:
    client = SimpleNamespace(attach_trade_store=lambda *_: None)
    manager = TradeStoreManager(kalshi_client=client, store_supplier=lambda: None)

    assert await manager.maybe_get() is None
