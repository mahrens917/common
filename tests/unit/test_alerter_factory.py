from __future__ import annotations

import sys
import types
import weakref

import pytest

from common import alerter_factory


class DummyAlerter:
    def __init__(self) -> None:
        self.cleanup_calls = 0

    async def cleanup(self) -> None:
        self.cleanup_calls += 1


def _install_fake_monitor_alerting_models():
    src_module = sys.modules.setdefault("src", types.ModuleType("src"))
    monitor_module = sys.modules.setdefault("src.monitor", types.ModuleType("src.monitor"))
    alerting_module = sys.modules.setdefault("src.monitor.alerting", types.ModuleType("src.monitor.alerting"))
    models_module = types.ModuleType("src.monitor.alerting.models")

    class AlerterError(Exception):
        pass

    models_module.AlerterError = AlerterError
    sys.modules["src.monitor.alerting.models"] = models_module

    src_module.monitor = monitor_module
    monitor_module.alerting = alerting_module
    alerting_module.models = models_module

    return AlerterError


def test_create_alerter_registers_shutdown_hook(monkeypatch):
    callbacks = []
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
    monkeypatch.setattr(alerter_factory, "ServiceAlerter", DummyAlerter)
    monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

    alerter = alerter_factory.create_alerter()

    assert isinstance(alerter, DummyAlerter)
    assert len(callbacks) == 1


def test_shutdown_hook_runs_cleanup(monkeypatch):
    _install_fake_monitor_alerting_models()

    callbacks = []
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
    monkeypatch.setattr(alerter_factory, "ServiceAlerter", DummyAlerter)
    monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

    alerter = alerter_factory.create_alerter()
    callbacks[0]()

    assert alerter.cleanup_calls == 1


def test_shutdown_hook_direct_cleanup_error_raises_cleanup_error(monkeypatch):
    AlerterError = _install_fake_monitor_alerting_models()

    callbacks = []
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
    monkeypatch.setattr(alerter_factory, "ServiceAlerter", DummyAlerter)
    monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

    def raise_alerter_error(_coro):
        _coro.close()
        raise AlerterError("boom")

    monkeypatch.setattr(alerter_factory.asyncio, "run", raise_alerter_error)

    _ = alerter_factory.create_alerter()
    with pytest.raises(alerter_factory.AlerterCleanupError):
        callbacks[0]()


def test_shutdown_hook_falls_back_to_new_event_loop_on_runtime_error(monkeypatch):
    _install_fake_monitor_alerting_models()

    callbacks = []
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
    monkeypatch.setattr(alerter_factory, "ServiceAlerter", DummyAlerter)
    monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

    alerter = alerter_factory.create_alerter()

    def raise_runtime_error(_coro):
        _coro.close()
        raise RuntimeError("no running event loop")

    monkeypatch.setattr(alerter_factory.asyncio, "run", raise_runtime_error)

    class FakeLoop:
        def __init__(self) -> None:
            self.closed = False

        def run_until_complete(self, coro) -> None:
            coro.close()
            alerter.cleanup_calls += 1

        def close(self) -> None:
            self.closed = True

    fake_loop = FakeLoop()
    monkeypatch.setattr(alerter_factory.asyncio, "new_event_loop", lambda: fake_loop)

    callbacks[0]()

    assert alerter.cleanup_calls == 1
    assert fake_loop.closed is True


def test_create_alerter_for_service(monkeypatch):
    callbacks = []
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
    monkeypatch.setattr(alerter_factory, "ServiceAlerter", DummyAlerter)
    monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

    alerter = alerter_factory.create_alerter_for_service("svc")

    assert isinstance(alerter, DummyAlerter)
    assert len(callbacks) == 1
