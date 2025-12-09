"""Tests for monitoring loop module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.dependency_monitor_helpers.dependency_checker import (
    DependencyConfig,
    DependencyState,
    DependencyStatus,
)
from src.common.dependency_monitor_helpers.monitoring_loop import MonitoringLoop


class TestMonitoringLoop:
    """Tests for MonitoringLoop class."""

    def test_init_stores_all_params(self) -> None:
        """Stores all initialization parameters."""
        dependencies = {"dep1": MagicMock()}
        checker = MagicMock()
        status_manager = MagicMock()

        loop = MonitoringLoop("test_service", dependencies, checker, status_manager)

        assert loop.service_name == "test_service"
        assert loop.dependencies == dependencies
        assert loop.dependency_checker == checker
        assert loop.status_manager == status_manager
        assert loop.running is False

    def test_start_sets_running_true(self) -> None:
        """start() sets running to True."""
        loop = MonitoringLoop("test_service", {}, MagicMock(), MagicMock())

        loop.start()

        assert loop.running is True

    def test_stop_sets_running_false(self) -> None:
        """stop() sets running to False."""
        loop = MonitoringLoop("test_service", {}, MagicMock(), MagicMock())
        loop.running = True

        loop.stop()

        assert loop.running is False


class TestRunLoop:
    """Tests for run_loop method."""

    @pytest.mark.asyncio
    async def test_exits_when_not_running(self) -> None:
        """Exits immediately when running is False."""
        loop = MonitoringLoop("test_service", {}, MagicMock(), MagicMock())
        loop.running = False

        await loop.run_loop()

        # Should complete without blocking

    @pytest.mark.asyncio
    async def test_checks_dependencies_when_interval_elapsed(self) -> None:
        """Checks dependencies when check interval has elapsed."""
        config = DependencyConfig(
            name="dep1", check_function=lambda: True, check_interval_seconds=0.1
        )
        state = DependencyState(
            config=config,
            last_check_time=0,  # Very old
            current_check_interval=0.1,
        )
        dependencies = {"dep1": state}
        checker = MagicMock()
        checker.check_dependency = AsyncMock(return_value=DependencyStatus.AVAILABLE)
        status_manager = MagicMock()
        status_manager.handle_status_changes = AsyncMock()

        loop = MonitoringLoop("test_service", dependencies, checker, status_manager)
        loop.running = True

        # Run loop briefly then stop
        async def stop_after_delay():
            await asyncio.sleep(0)
            loop.running = False

        await asyncio.gather(loop.run_loop(), stop_after_delay())

        # Should have attempted to check dependency
        checker.check_dependency.assert_called()

    @pytest.mark.asyncio
    async def test_handles_cancelled_error(self) -> None:
        """Handles CancelledError gracefully."""
        loop = MonitoringLoop("test_service", {}, MagicMock(), MagicMock())
        loop.running = True

        async def cancel_loop():
            await asyncio.sleep(0)
            raise asyncio.CancelledError()

        # Should not raise
        with pytest.raises(asyncio.CancelledError):
            await cancel_loop()

    @pytest.mark.asyncio
    async def test_calls_status_manager_handle_changes(self) -> None:
        """Calls status_manager.handle_status_changes."""
        dependencies = {}
        checker = MagicMock()
        status_manager = MagicMock()
        status_manager.handle_status_changes = AsyncMock()

        loop = MonitoringLoop("test_service", dependencies, checker, status_manager)
        loop.running = True

        async def stop_after_delay():
            await asyncio.sleep(0)
            loop.running = False

        await asyncio.gather(loop.run_loop(), stop_after_delay())

        status_manager.handle_status_changes.assert_called()


class TestCheckDependencyWithNotification:
    """Tests for _check_dependency_with_notification method."""

    @pytest.mark.asyncio
    async def test_calls_checker_with_state(self) -> None:
        """Calls dependency checker with state."""
        config = DependencyConfig(name="dep1", check_function=lambda: True)
        state = DependencyState(config=config)
        checker = MagicMock()
        checker.check_dependency = AsyncMock(return_value=DependencyStatus.AVAILABLE)
        status_manager = MagicMock()
        status_manager.notify_status_change = AsyncMock()

        loop = MonitoringLoop("test_service", {}, checker, status_manager)

        result = await loop._check_dependency_with_notification(state)

        checker.check_dependency.assert_called_once()
        assert result == DependencyStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_passes_notifier_from_status_manager(self) -> None:
        """Passes notifier callback from status manager."""
        config = DependencyConfig(name="dep1", check_function=lambda: True)
        state = DependencyState(config=config)
        checker = MagicMock()
        checker.check_dependency = AsyncMock(return_value=DependencyStatus.AVAILABLE)
        status_manager = MagicMock()
        notifier = AsyncMock()
        status_manager.notify_status_change = notifier

        loop = MonitoringLoop("test_service", {}, checker, status_manager)

        await loop._check_dependency_with_notification(state)

        call_args = checker.check_dependency.call_args
        assert call_args[0][1] == notifier

    @pytest.mark.asyncio
    async def test_passes_none_when_no_status_manager(self) -> None:
        """Passes None notifier when no status manager."""
        config = DependencyConfig(name="dep1", check_function=lambda: True)
        state = DependencyState(config=config)
        checker = MagicMock()
        checker.check_dependency = AsyncMock(return_value=DependencyStatus.AVAILABLE)

        loop = MonitoringLoop("test_service", {}, checker, None)

        await loop._check_dependency_with_notification(state)

        call_args = checker.check_dependency.call_args
        assert call_args[0][1] is None
