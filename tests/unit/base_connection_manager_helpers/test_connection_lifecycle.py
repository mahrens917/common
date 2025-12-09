"""Tests for connection lifecycle module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.base_connection_manager_helpers.connection_lifecycle import (
    ConnectionLifecycleManager,
)

DEFAULT_MONITOR_CALL_ITERATIONS = 2


class TestConnectionLifecycleManagerInit:
    """Tests for ConnectionLifecycleManager initialization."""

    def test_initializes_with_service_name(self) -> None:
        """Initializes with service name."""
        manager = ConnectionLifecycleManager(service_name="test_service")

        assert manager.service_name == "test_service"
        assert manager.health_check_task is None
        assert manager.reconnection_task is None
        assert manager.shutdown_requested is False


class TestConnectionLifecycleManagerStartHealthMonitoring:
    """Tests for ConnectionLifecycleManager.start_health_monitoring."""

    @pytest.mark.asyncio
    async def test_calls_monitor_function(self) -> None:
        """Calls monitor function in loop."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        monitor_fn = AsyncMock()
        call_count = 0

        async def mock_monitor():
            nonlocal call_count
            call_count += 1
            if call_count >= DEFAULT_MONITOR_CALL_ITERATIONS:
                manager.shutdown_requested = True

        monitor_fn.side_effect = mock_monitor

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await manager.start_health_monitoring(monitor_fn, 0.01)

        assert call_count >= DEFAULT_MONITOR_CALL_ITERATIONS

    @pytest.mark.asyncio
    async def test_sleeps_between_checks(self) -> None:
        """Sleeps for interval between checks."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        call_count = 0

        async def mock_monitor():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                manager.shutdown_requested = True

        monitor_fn = AsyncMock(side_effect=mock_monitor)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await manager.start_health_monitoring(monitor_fn, 5.0)

        mock_sleep.assert_called_with(5.0)

    @pytest.mark.asyncio
    async def test_raises_on_connection_error(self) -> None:
        """Raises on ConnectionError from monitor function."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        monitor_fn = AsyncMock(side_effect=ConnectionError("Connection lost"))

        with pytest.raises(ConnectionError):
            await manager.start_health_monitoring(monitor_fn, 0.01)

    @pytest.mark.asyncio
    async def test_raises_on_timeout_error(self) -> None:
        """Raises on TimeoutError from monitor function."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        monitor_fn = AsyncMock(side_effect=TimeoutError("Timeout"))

        with pytest.raises(TimeoutError):
            await manager.start_health_monitoring(monitor_fn, 0.01)

    @pytest.mark.asyncio
    async def test_raises_on_runtime_error(self) -> None:
        """Raises on RuntimeError from monitor function."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        monitor_fn = AsyncMock(side_effect=RuntimeError("Runtime error"))

        with pytest.raises(RuntimeError):
            await manager.start_health_monitoring(monitor_fn, 0.01)


class TestConnectionLifecycleManagerStartReconnectionTask:
    """Tests for ConnectionLifecycleManager.start_reconnection_task."""

    @pytest.mark.asyncio
    async def test_creates_task_when_none_exists(self) -> None:
        """Creates task when no existing task."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        reconnect_fn = AsyncMock()

        manager.start_reconnection_task(reconnect_fn)

        assert manager.reconnection_task is not None
        # Clean up
        manager.reconnection_task.cancel()

    @pytest.mark.asyncio
    async def test_creates_task_when_previous_is_done(self) -> None:
        """Creates new task when previous is done."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        done_task = MagicMock()
        done_task.done.return_value = True
        manager.reconnection_task = done_task
        reconnect_fn = AsyncMock()

        manager.start_reconnection_task(reconnect_fn)

        assert manager.reconnection_task is not done_task
        # Clean up
        if hasattr(manager.reconnection_task, "cancel"):
            manager.reconnection_task.cancel()

    def test_does_not_create_task_when_running(self) -> None:
        """Does not create new task when existing is running."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        running_task = MagicMock()
        running_task.done.return_value = False
        manager.reconnection_task = running_task
        reconnect_fn = AsyncMock()

        manager.start_reconnection_task(reconnect_fn)

        assert manager.reconnection_task is running_task


class TestConnectionLifecycleManagerStop:
    """Tests for ConnectionLifecycleManager.stop."""

    @pytest.mark.asyncio
    async def test_sets_shutdown_requested(self) -> None:
        """Sets shutdown_requested flag."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        cleanup_fn = AsyncMock()

        await manager.stop(cleanup_fn)

        assert manager.shutdown_requested is True

    @pytest.mark.asyncio
    async def test_cancels_health_check_task(self) -> None:
        """Cancels health check task if running."""
        manager = ConnectionLifecycleManager(service_name="test_service")

        async def long_running():
            await asyncio.sleep(100)

        manager.health_check_task = asyncio.create_task(long_running())
        cleanup_fn = AsyncMock()

        await manager.stop(cleanup_fn)

        assert manager.health_check_task.cancelled()

    @pytest.mark.asyncio
    async def test_cancels_reconnection_task(self) -> None:
        """Cancels reconnection task if running."""
        manager = ConnectionLifecycleManager(service_name="test_service")

        async def long_running():
            await asyncio.sleep(100)

        manager.reconnection_task = asyncio.create_task(long_running())
        cleanup_fn = AsyncMock()

        await manager.stop(cleanup_fn)

        assert manager.reconnection_task.cancelled()

    @pytest.mark.asyncio
    async def test_calls_cleanup_function(self) -> None:
        """Calls cleanup function."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        cleanup_fn = AsyncMock()

        await manager.stop(cleanup_fn)

        cleanup_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_no_tasks(self) -> None:
        """Handles case with no running tasks."""
        manager = ConnectionLifecycleManager(service_name="test_service")
        cleanup_fn = AsyncMock()

        # Should not raise
        await manager.stop(cleanup_fn)

        cleanup_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_already_done_tasks(self) -> None:
        """Handles tasks that are already done."""
        manager = ConnectionLifecycleManager(service_name="test_service")

        async def quick_task():
            pass

        manager.health_check_task = asyncio.create_task(quick_task())
        await asyncio.sleep(0)  # Let task complete
        cleanup_fn = AsyncMock()

        # Should not raise
        await manager.stop(cleanup_fn)

        cleanup_fn.assert_called_once()
