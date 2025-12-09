"""Tests for startup coordinator module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.base_connection_manager_helpers.startup_coordinator import StartupCoordinator


class TestStartupCoordinatorInit:
    """Tests for StartupCoordinator initialization."""

    def test_initializes_with_dependencies(self) -> None:
        """Initializes with all required dependencies."""
        state_mgr = MagicMock()
        lifecycle_mgr = MagicMock()

        coordinator = StartupCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=lifecycle_mgr,
        )

        assert coordinator.service_name == "test_service"
        assert coordinator.state_manager is state_mgr
        assert coordinator.lifecycle_manager is lifecycle_mgr
        assert coordinator.health_check_task is None


class TestStartupCoordinatorStart:
    """Tests for StartupCoordinator.start."""

    @pytest.mark.asyncio
    async def test_initializes_state_tracker(self) -> None:
        """Initializes state tracker on start."""
        state_mgr = MagicMock()
        state_mgr._initialize_state_tracker = AsyncMock()
        lifecycle_mgr = MagicMock()

        coordinator = StartupCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=lifecycle_mgr,
        )
        connect_fn = AsyncMock(return_value=True)
        health_fn = AsyncMock()

        await coordinator.start(connect_fn, health_fn)

        state_mgr._initialize_state_tracker.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_true_on_successful_connection(self) -> None:
        """Returns True when connection succeeds."""
        state_mgr = MagicMock()
        state_mgr._initialize_state_tracker = AsyncMock()
        lifecycle_mgr = MagicMock()

        coordinator = StartupCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=lifecycle_mgr,
        )
        connect_fn = AsyncMock(return_value=True)
        health_fn = AsyncMock()

        result = await coordinator.start(connect_fn, health_fn)

        assert result is True
        connect_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_health_check_task_on_success(self) -> None:
        """Creates health check task when connection succeeds."""
        state_mgr = MagicMock()
        state_mgr._initialize_state_tracker = AsyncMock()
        lifecycle_mgr = MagicMock()

        coordinator = StartupCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=lifecycle_mgr,
        )
        connect_fn = AsyncMock(return_value=True)
        health_fn = AsyncMock()

        await coordinator.start(connect_fn, health_fn)

        assert coordinator.health_check_task is not None
        # Clean up the task
        coordinator.health_check_task.cancel()

    @pytest.mark.asyncio
    async def test_returns_false_on_failed_connection(self) -> None:
        """Returns False when connection fails."""
        state_mgr = MagicMock()
        state_mgr._initialize_state_tracker = AsyncMock()
        lifecycle_mgr = MagicMock()

        coordinator = StartupCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=lifecycle_mgr,
        )
        connect_fn = AsyncMock(return_value=False)
        health_fn = AsyncMock()

        result = await coordinator.start(connect_fn, health_fn)

        assert result is False

    @pytest.mark.asyncio
    async def test_does_not_create_health_task_on_failure(self) -> None:
        """Does not create health check task when connection fails."""
        state_mgr = MagicMock()
        state_mgr._initialize_state_tracker = AsyncMock()
        lifecycle_mgr = MagicMock()

        coordinator = StartupCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=lifecycle_mgr,
        )
        connect_fn = AsyncMock(return_value=False)
        health_fn = AsyncMock()

        await coordinator.start(connect_fn, health_fn)

        assert coordinator.health_check_task is None

    @pytest.mark.asyncio
    async def test_logs_success_message(self) -> None:
        """Logs success message on successful connection."""
        state_mgr = MagicMock()
        state_mgr._initialize_state_tracker = AsyncMock()
        lifecycle_mgr = MagicMock()

        coordinator = StartupCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=lifecycle_mgr,
        )
        connect_fn = AsyncMock(return_value=True)
        health_fn = AsyncMock()

        with patch.object(coordinator.logger, "info") as mock_log:
            await coordinator.start(connect_fn, health_fn)

        # Should log both starting and started messages
        assert mock_log.call_count == 2
        # Clean up
        coordinator.health_check_task.cancel()

    @pytest.mark.asyncio
    async def test_logs_error_on_failure(self) -> None:
        """Logs error message on failed connection."""
        state_mgr = MagicMock()
        state_mgr._initialize_state_tracker = AsyncMock()
        lifecycle_mgr = MagicMock()

        coordinator = StartupCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=lifecycle_mgr,
        )
        connect_fn = AsyncMock(return_value=False)
        health_fn = AsyncMock()

        with patch.object(coordinator.logger, "error") as mock_log:
            await coordinator.start(connect_fn, health_fn)

        mock_log.assert_called_once()
        assert "Failed" in mock_log.call_args[0][0]


class TestStartupCoordinatorStop:
    """Tests for StartupCoordinator.stop."""

    @pytest.mark.asyncio
    async def test_delegates_to_lifecycle_manager(self) -> None:
        """Delegates stop to lifecycle manager."""
        state_mgr = MagicMock()
        lifecycle_mgr = MagicMock()
        lifecycle_mgr.stop = AsyncMock()

        coordinator = StartupCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=lifecycle_mgr,
        )
        cleanup_fn = AsyncMock()

        await coordinator.stop(cleanup_fn)

        lifecycle_mgr.stop.assert_called_once_with(cleanup_fn)
