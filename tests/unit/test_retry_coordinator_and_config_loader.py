"""Targeted coverage tests for retry coordinator and daily max config loader."""

from __future__ import annotations

import asyncio

import pytest

from src.common.base_connection_manager_helpers.retry_coordinator import RetryCoordinator
from src.common.connection_state import ConnectionState
from src.common.daily_max_state_helpers.config_loader import (
    ConfigLoader,
    MetarConfigLoadError,
)


class _DummyMetrics:
    def __init__(self):
        self.consecutive_failures = 1
        self.total_reconnection_attempts = 0


class _DummyMetricsTracker:
    def __init__(self):
        self.metrics = _DummyMetrics()
        self.successes = 0
        self.failures = 0
        self.total_connections = 0

    def record_success(self):
        self.successes += 1

    def record_failure(self):
        self.failures += 1

    def get_metrics(self):
        return self.metrics

    def increment_total_connections(self):
        self.total_connections += 1


class _DummyStateManager:
    def __init__(self):
        self.transitions: list[tuple[ConnectionState, str | None]] = []

    def transition_state(self, state: ConnectionState, ctx: str | None = None):
        self.transitions.append((state, ctx))


class _DummyNotification:
    def __init__(self):
        self.calls: list[tuple[bool, str]] = []

    async def send_connection_notification(self, is_connected: bool, details: str = ""):
        self.calls.append((is_connected, details))


class _DummyLifecycle:
    shutdown_requested = False


class _DummyReconnectionHandler:
    def __init__(self, retries: list[bool]):
        self.retries = retries
        self.backoff_calls = 0

    async def apply_backoff(self):
        self.backoff_calls += 1

    def should_retry(self):
        # Return the current flag and keep last value for subsequent calls
        if len(self.retries) > 1:
            return self.retries.pop(0)
        return self.retries[0]


@pytest.mark.asyncio
async def test_retry_coordinator_success_flow():
    metrics = _DummyMetricsTracker()
    state_manager = _DummyStateManager()
    reconnection_handler = _DummyReconnectionHandler([True])
    lifecycle = _DummyLifecycle()
    notification = _DummyNotification()

    coordinator = RetryCoordinator(
        service_name="svc",
        state_manager=state_manager,
        metrics_tracker=metrics,
        reconnection_handler=reconnection_handler,
        lifecycle_manager=lifecycle,
        notification_handler=notification,
        max_consecutive_failures=3,
    )

    async def establish():
        return True

    assert await coordinator.connect_with_retry(establish) is True
    assert (ConnectionState.CONNECTING, None) in state_manager.transitions
    assert (ConnectionState.READY, None) in state_manager.transitions
    assert notification.calls[0][0] is False  # Lost connection notice
    assert notification.calls[-1][0] is True  # Restored connection notice
    assert metrics.total_connections == 1
    assert reconnection_handler.backoff_calls == 1


@pytest.mark.asyncio
async def test_retry_coordinator_raises_when_no_more_retries():
    metrics = _DummyMetricsTracker()
    state_manager = _DummyStateManager()
    # Retry once, then stop
    reconnection_handler = _DummyReconnectionHandler([True, False])
    lifecycle = _DummyLifecycle()
    notification = _DummyNotification()

    coordinator = RetryCoordinator(
        service_name="svc",
        state_manager=state_manager,
        metrics_tracker=metrics,
        reconnection_handler=reconnection_handler,
        lifecycle_manager=lifecycle,
        notification_handler=notification,
        max_consecutive_failures=1,
    )

    async def establish():
        raise ConnectionError("boom")

    with pytest.raises(ConnectionError):
        await coordinator.connect_with_retry(establish)
    assert any(state == ConnectionState.FAILED for state, _ in state_manager.transitions)
    # ensure backoff attempted even on failure
    assert reconnection_handler.backoff_calls == 1


def test_config_loader_success_and_errors(monkeypatch):
    """Exercise ConfigLoader happy path and error handling."""
    loader = ConfigLoader()

    class _StubLoader:
        def __init__(self):
            self.config_dir = loader._loader.config_dir
            self.loaded = False

        def load_json_file(self, name):
            self.loaded = True
            if name == "missing":
                raise FileNotFoundError()
            return {"data_sources": {"primary": {"url": "http://example.com"}}}

        def get_section(self, data, section):
            if section not in data:
                raise RuntimeError("missing section")
            return data[section]

    stub = _StubLoader()
    monkeypatch.setattr(loader, "_loader", stub)

    # Happy path
    data_sources = loader.load_metar_config()
    assert data_sources["primary"]["url"] == "http://example.com"

    # Missing file
    stub.load_json_file = lambda _name: (_ for _ in ()).throw(FileNotFoundError())
    with pytest.raises(MetarConfigLoadError):
        loader.load_metar_config()

    # Empty data
    stub.load_json_file = lambda _name: {"data_sources": {}}
    with pytest.raises(MetarConfigLoadError):
        loader.load_metar_config()
