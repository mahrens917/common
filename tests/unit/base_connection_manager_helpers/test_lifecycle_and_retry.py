import asyncio
from types import SimpleNamespace

import pytest

from common.base_connection_manager_helpers.connection_lifecycle import (
    ConnectionLifecycleManager,
)
from common.base_connection_manager_helpers.health_monitor import ConnectionHealthMonitor
from common.base_connection_manager_helpers.notification_helpers import (
    send_connection_notification,
)
from common.base_connection_manager_helpers.retry_coordinator import RetryCoordinator
from common.base_connection_manager_helpers.retry_logic import connect_with_retry
from common.connection_state import ConnectionState


class _StubMetrics:
    def __init__(self):
        self.consecutive_failures = 0
        self.total_reconnection_attempts = 0
        self.total_connections = 0


class _StubMetricsTracker:
    def __init__(self):
        self.metrics = _StubMetrics()

    def get_metrics(self):
        return self.metrics

    def increment_total_connections(self):
        self.metrics.total_connections += 1

    def record_success(self):
        self.metrics.consecutive_failures = 0

    def record_failure(self):
        self.metrics.consecutive_failures += 1


class _StubStateManager:
    def __init__(self):
        self.state = ConnectionState.DISCONNECTED
        self.state_tracker = SimpleNamespace(calls=[])

    def transition_state(self, state, error_context=None):
        self.state = state
        self.state_tracker.calls.append((state, error_context))


class _DummyLifecycle(ConnectionLifecycleManager):
    def __init__(self):
        super().__init__("svc")


@pytest.mark.asyncio
async def test_connection_health_monitor_counts_and_threshold():
    monitor = ConnectionHealthMonitor("svc")
    assert monitor.get_failure_count() == 0
    monitor.increment_failures()
    monitor.increment_failures()
    assert monitor.get_failure_count() == 2
    assert monitor.should_raise_error(2)
    monitor.reset_failures()
    assert monitor.get_failure_count() == 0


@pytest.mark.asyncio
async def test_notification_helper_sends_metrics(monkeypatch):
    sent = {}

    class Tracker:
        async def store_service_metrics(self, name, metrics):
            sent["metrics"] = (name, metrics)
            return True

    class NotificationHandler:
        def __init__(self):
            self.notifications = []

        async def send_connection_notification(self, is_connected, details):
            self.notifications.append((is_connected, details))

    class Manager:
        def __init__(self):
            self.service_name = "svc"
            self.notification_handler = NotificationHandler()
            self.state_tracker = Tracker()
            self.metrics_tracker = SimpleNamespace(get_metrics=lambda: {"ok": True})

    manager = Manager()
    await send_connection_notification(manager, True, "connected")
    assert manager.notification_handler.notifications == [(True, "connected")]
    assert sent["metrics"] == ("svc", {"ok": True})


@pytest.mark.asyncio
async def test_connection_lifecycle_stop_cancels_tasks(monkeypatch):
    lifecycle = ConnectionLifecycleManager("svc")
    lifecycle.health_check_task = asyncio.create_task(asyncio.sleep(10))
    lifecycle.reconnection_task = asyncio.create_task(asyncio.sleep(10))

    await lifecycle.stop(cleanup_func=lambda: asyncio.sleep(0))
    assert lifecycle.shutdown_requested is True
    assert lifecycle.health_check_task.cancelled()
    assert lifecycle.reconnection_task.cancelled()


@pytest.mark.asyncio
async def test_connect_with_retry_success_and_failure(monkeypatch):
    metrics_tracker = _StubMetricsTracker()
    manager = SimpleNamespace(
        service_name="svc",
        metrics_tracker=metrics_tracker,
        shutdown_requested=False,
        config=SimpleNamespace(max_consecutive_failures=2),
        calculate_backoff_delay=lambda: 0,
        state=ConnectionState.DISCONNECTED,
    )
    transition_events = []

    def transition_state(state, error=None):
        transition_events.append((state, error))
        manager.state = state

    async def establish_connection():
        return True

    async def send_notification(is_connected, details):
        transition_events.append(("notify", is_connected, details))

    result = await connect_with_retry(manager, establish_connection, send_notification, transition_state)
    assert result is True
    assert manager.state == ConnectionState.READY
    assert metrics_tracker.metrics.total_connections == 1

    # Simulate consecutive failures to trigger ConnectionError
    metrics_tracker.metrics.consecutive_failures = manager.config.max_consecutive_failures - 1

    async def failing_establish():
        metrics_tracker.metrics.consecutive_failures = manager.config.max_consecutive_failures
        raise RuntimeError("boom")

    with pytest.raises(ConnectionError):
        await connect_with_retry(
            manager,
            establish_connection=failing_establish,
            send_notification=send_notification,
            transition_state=transition_state,
        )


@pytest.mark.asyncio
async def test_retry_coordinator_transitions_and_notifications(monkeypatch):
    state_manager = _StubStateManager()
    metrics_tracker = _StubMetricsTracker()

    class ReconnectionHandler:
        def __init__(self):
            self.retries = 0

        def should_retry(self):
            self.retries += 1
            return self.retries < 3

        async def apply_backoff(self):
            return None

    notifications = []

    class NotificationHandler:
        async def send_connection_notification(self, is_connected, details):
            notifications.append((is_connected, details))

    coordinator = RetryCoordinator(
        "svc",
        state_manager=state_manager,
        metrics_tracker=metrics_tracker,
        reconnection_handler=ReconnectionHandler(),
        lifecycle_manager=_DummyLifecycle(),
        notification_handler=NotificationHandler(),
        max_consecutive_failures=3,
    )

    async def establish_connection():
        # succeed on second attempt
        return metrics_tracker.metrics.total_reconnection_attempts > 0

    success = await coordinator.connect_with_retry(establish_connection)
    assert success is True
    assert notifications[-1][0] is True
    assert state_manager.state == ConnectionState.READY
