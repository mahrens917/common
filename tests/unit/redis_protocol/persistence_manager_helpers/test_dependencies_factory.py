from __future__ import annotations

from types import SimpleNamespace

from src.common.redis_protocol.persistence_manager_helpers.dependencies_factory import (
    RedisPersistenceManagerDependenciesFactory,
)


def test_create_sets_redis_on_connection(monkeypatch):
    captured = SimpleNamespace(set_called=False, redis_arg=None)

    class FakeConnection:
        def __init__(self):
            self.set_calls = 0

        def set_redis(self, redis):
            captured.set_called = True
            captured.redis_arg = redis
            self.set_calls += 1

    monkeypatch.setattr(
        "src.common.redis_protocol.persistence_manager_helpers.dependencies_factory.ConnectionManager",
        FakeConnection,
    )

    deps = RedisPersistenceManagerDependenciesFactory.create(redis="redis-client")

    assert captured.set_called is True
    assert captured.redis_arg == "redis-client"
    # Downstream helpers should still be created
    assert deps.connection is not None
    assert deps.configorchestrator is not None
    assert deps.snapshot is not None
    assert deps.keyscanner is not None
    assert deps.dataserializer is not None
    assert deps.validation is not None
