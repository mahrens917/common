from typing import cast

import pytest

from common.redis_protocol.connection_store import ConnectionStore
from common.redis_protocol.connection_store_helpers.initialization_manager import (
    InitializationManager,
)


class _ParentStore(ConnectionStore):
    def __init__(self):
        super().__init__()
        self.redis_client = None
        self.get_client_calls = 0
        self.connection_states_key = "states"
        self.reconnection_events_key = "events"

    async def get_client(self):
        self.get_client_calls += 1
        return self.redis_client


@pytest.mark.asyncio
async def test_initialization_manager(monkeypatch):
    parent = _ParentStore()

    async def fake_get_redis_client():
        return "redis-client"

    monkeypatch.setattr(
        "common.redis_protocol.connection_pool_core.get_redis_client",
        fake_get_redis_client,
    )

    # Track helper construction
    constructed = {}

    class _StateManager:
        def __init__(self, getter, key):
            constructed["state"] = (getter, key)

    class _MetricsManager:
        def __init__(self, getter):
            constructed["metrics"] = getter

    class _ReconnectionEventManager:
        def __init__(self, getter, key):
            constructed["reconnect"] = (getter, key)

    monkeypatch.setattr(
        "common.redis_protocol.connection_store_helpers.state_manager.StateManager",
        _StateManager,
    )
    monkeypatch.setattr(
        "common.redis_protocol.connection_store_helpers.metrics_manager.MetricsManager",
        _MetricsManager,
    )
    monkeypatch.setattr(
        "common.redis_protocol.connection_store_helpers.reconnection_event_manager.ReconnectionEventManager",
        _ReconnectionEventManager,
    )

    manager = InitializationManager(cast(ConnectionStore, parent))
    await manager.ensure_initialized()

    assert parent.redis_client == "redis-client"
    assert constructed["state"][1] == "states"
    assert constructed["reconnect"][1] == "events"
    assert parent.get_client_calls == 0  # getters are passed, not invoked yet

    # Second call should be a no-op when redis_client already set
    parent.get_client_calls = 0
    await manager.ensure_initialized()
    assert parent.get_client_calls == 0
