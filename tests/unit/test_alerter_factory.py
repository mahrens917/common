from __future__ import annotations

import sys
import types
import weakref

import pytest
from redis.exceptions import RedisError

from common import alerter_factory

TEST_SERVICE_NAME = "test_service"


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


def test_register_shutdown_hook_is_idempotent(monkeypatch):
    callbacks = []
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
    monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

    alerter = DummyAlerter()
    alerter_factory._register_shutdown_hook(alerter)
    alerter_factory._register_shutdown_hook(alerter)

    assert len(callbacks) == 1


def test_fallback_alerter_used_when_alerter_import_fails(monkeypatch):
    """Test that _FallbackAlerter is used when common.alerter module is not available."""
    import importlib

    # Save original module state
    original_alerter = sys.modules.get("common.alerter")

    try:
        # Remove the alerter module to trigger ImportError
        sys.modules["common.alerter"] = None

        # Force reload of alerter_factory to trigger the import error path
        importlib.reload(alerter_factory)

        # Create an alerter - should use _FallbackAlerter
        callbacks = []
        monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
        monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

        alerter = alerter_factory.create_alerter()

        # Should create successfully even without the monitor module
        assert alerter is not None
        assert hasattr(alerter, "cleanup")
    finally:
        # Restore original module state
        if original_alerter is not None:
            sys.modules["common.alerter"] = original_alerter
        elif "common.alerter" in sys.modules:
            del sys.modules["common.alerter"]
        # Reload to restore normal state
        importlib.reload(alerter_factory)


def _install_fake_common_alerting_models():
    """Install fake common.alerting.models module for testing."""
    common_module = sys.modules.setdefault("common.alerting", types.ModuleType("common.alerting"))
    models_module = types.ModuleType("common.alerting.models")

    class AlerterError(Exception):
        pass

    models_module.AlerterError = AlerterError
    sys.modules["common.alerting.models"] = models_module
    common_module.models = models_module

    return AlerterError


def test_shutdown_hook_handles_common_alerter_error_import(monkeypatch):
    """Test that shutdown hook handles CommonAlerterError import path."""
    CommonAlerterError = _install_fake_common_alerting_models()

    callbacks = []
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
    monkeypatch.setattr(alerter_factory, "ServiceAlerter", DummyAlerter)
    monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

    def raise_common_alerter_error(_coro):
        _coro.close()
        raise CommonAlerterError("common alerter error")

    monkeypatch.setattr(alerter_factory.asyncio, "run", raise_common_alerter_error)

    _ = alerter_factory.create_alerter()
    with pytest.raises(alerter_factory.AlerterCleanupError):
        callbacks[0]()


def test_shutdown_hook_handles_new_event_loop_cleanup_error(monkeypatch):
    """Test that cleanup errors in new event loop path are handled."""
    _install_fake_monitor_alerting_models()

    callbacks = []
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
    monkeypatch.setattr(alerter_factory, "ServiceAlerter", DummyAlerter)
    monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

    _ = alerter_factory.create_alerter()

    def raise_runtime_error(_coro):
        _coro.close()
        raise RuntimeError("no running event loop")

    monkeypatch.setattr(alerter_factory.asyncio, "run", raise_runtime_error)

    class FakeLoop:
        def __init__(self) -> None:
            self.closed = False

        def run_until_complete(self, _coro) -> None:
            _coro.close()
            raise RedisError("redis connection failed")

        def close(self) -> None:
            self.closed = True

    fake_loop = FakeLoop()
    monkeypatch.setattr(alerter_factory.asyncio, "new_event_loop", lambda: fake_loop)

    with pytest.raises(alerter_factory.AlerterCleanupError):
        callbacks[0]()

    assert fake_loop.closed is True


def test_shutdown_hook_handles_missing_common_alerter_error(monkeypatch):
    """Test that shutdown hook handles missing CommonAlerterError gracefully."""
    # Ensure common.alerting.models is not available
    if "common.alerting.models" in sys.modules:
        del sys.modules["common.alerting.models"]
    if "common.alerting" in sys.modules:
        del sys.modules["common.alerting"]

    _install_fake_monitor_alerting_models()

    callbacks = []
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
    monkeypatch.setattr(alerter_factory, "ServiceAlerter", DummyAlerter)
    monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

    alerter = alerter_factory.create_alerter()

    # Trigger the cleanup which will attempt to import CommonAlerterError
    callbacks[0]()

    assert alerter.cleanup_calls == 1


def test_shutdown_hook_handles_missing_monitor_alerter_error(monkeypatch):
    """Test that shutdown hook handles missing MonitorAlerterError gracefully."""
    # Ensure src.monitor.alerting.models is not available
    if "src.monitor.alerting.models" in sys.modules:
        del sys.modules["src.monitor.alerting.models"]
    if "src.monitor.alerting" in sys.modules:
        del sys.modules["src.monitor.alerting"]
    if "src.monitor" in sys.modules:
        del sys.modules["src.monitor"]

    callbacks = []
    monkeypatch.setattr(alerter_factory, "_shutdown_registry", weakref.WeakSet())
    monkeypatch.setattr(alerter_factory, "ServiceAlerter", DummyAlerter)
    monkeypatch.setattr(alerter_factory.atexit, "register", lambda fn: callbacks.append(fn))

    alerter = alerter_factory.create_alerter()

    # Trigger the cleanup which will attempt to import MonitorAlerterError
    callbacks[0]()

    assert alerter.cleanup_calls == 1


async def test_fallback_alerter_cleanup_returns_none():
    """Test that _FallbackAlerter.cleanup() returns None."""
    # Create a _FallbackAlerter directly
    fallback = alerter_factory._FallbackAlerter()
    result = await fallback.cleanup()
    assert result is None
