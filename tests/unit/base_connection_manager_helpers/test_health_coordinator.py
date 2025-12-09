"""Tests for health coordinator module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.base_connection_manager_helpers.health_coordinator import HealthCoordinator
from src.common.connection_state import ConnectionState


class TestHealthCoordinatorInit:
    """Tests for HealthCoordinator initialization."""

    def test_initializes_with_dependencies(self) -> None:
        """Initializes with all required dependencies."""
        state_mgr = MagicMock()
        lifecycle_mgr = MagicMock()
        health_mon = MagicMock()

        coordinator = HealthCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=lifecycle_mgr,
            health_monitor=health_mon,
            health_check_interval=30.0,
            max_consecutive_failures=5,
        )

        assert coordinator.service_name == "test_service"
        assert coordinator.state_manager is state_mgr
        assert coordinator.lifecycle_manager is lifecycle_mgr
        assert coordinator.health_monitor is health_mon
        assert coordinator.health_check_interval == 30.0
        assert coordinator.max_consecutive_failures == 5
        assert coordinator.reconnection_task is None


class TestHealthCoordinatorTransitionState:
    """Tests for HealthCoordinator._transition_state."""

    def test_delegates_to_state_manager(self) -> None:
        """Delegates state transition to state manager."""
        state_mgr = MagicMock()
        coordinator = HealthCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=MagicMock(),
            health_monitor=MagicMock(),
            health_check_interval=30.0,
            max_consecutive_failures=5,
        )

        coordinator._transition_state(ConnectionState.READY, "context")

        state_mgr.transition_state.assert_called_once_with(ConnectionState.READY, "context")

    def test_works_without_error_context(self) -> None:
        """Works without error context."""
        state_mgr = MagicMock()
        coordinator = HealthCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=MagicMock(),
            health_monitor=MagicMock(),
            health_check_interval=30.0,
            max_consecutive_failures=5,
        )

        coordinator._transition_state(ConnectionState.DISCONNECTED)

        state_mgr.transition_state.assert_called_once_with(ConnectionState.DISCONNECTED, None)


class TestHealthCoordinatorProcessHealthCycle:
    """Tests for HealthCoordinator._process_health_cycle."""

    @pytest.mark.asyncio
    async def test_handles_ready_state(self) -> None:
        """Handles READY state by checking health."""
        state_mgr = MagicMock()
        state_mgr.get_state.return_value = ConnectionState.READY
        coordinator = HealthCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=MagicMock(),
            health_monitor=MagicMock(),
            health_check_interval=30.0,
            max_consecutive_failures=5,
        )
        health_checker = MagicMock()
        health_checker.check_and_handle_failure = AsyncMock(return_value=(True, None))
        reconnection_mgr = MagicMock()
        check_fn = AsyncMock()
        connect_fn = AsyncMock()

        result = await coordinator._process_health_cycle(
            check_fn, connect_fn, health_checker, reconnection_mgr
        )

        assert result is True
        health_checker.check_and_handle_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_disconnected_state(self) -> None:
        """Handles DISCONNECTED state by attempting reconnection."""
        state_mgr = MagicMock()
        state_mgr.get_state.return_value = ConnectionState.DISCONNECTED
        coordinator = HealthCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=MagicMock(),
            health_monitor=MagicMock(),
            health_check_interval=30.0,
            max_consecutive_failures=5,
        )
        health_checker = MagicMock()
        reconnection_mgr = MagicMock()
        reconnection_mgr.handle_disconnected = AsyncMock(return_value=(True, None))
        check_fn = AsyncMock()
        connect_fn = AsyncMock()

        result = await coordinator._process_health_cycle(
            check_fn, connect_fn, health_checker, reconnection_mgr
        )

        assert result is True
        reconnection_mgr.handle_disconnected.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_true_for_other_states(self) -> None:
        """Returns True for other connection states."""
        state_mgr = MagicMock()
        state_mgr.get_state.return_value = ConnectionState.CONNECTING
        coordinator = HealthCoordinator(
            service_name="test_service",
            state_manager=state_mgr,
            lifecycle_manager=MagicMock(),
            health_monitor=MagicMock(),
            health_check_interval=30.0,
            max_consecutive_failures=5,
        )
        health_checker = MagicMock()
        reconnection_mgr = MagicMock()

        result = await coordinator._process_health_cycle(
            AsyncMock(), AsyncMock(), health_checker, reconnection_mgr
        )

        assert result is True


class TestHealthCoordinatorHandleMonitoringError:
    """Tests for HealthCoordinator._handle_monitoring_error."""

    @pytest.mark.asyncio
    async def test_increments_failure_count(self) -> None:
        """Increments failure count on error."""
        health_mon = MagicMock()
        health_mon.should_raise_error.return_value = False
        coordinator = HealthCoordinator(
            service_name="test_service",
            state_manager=MagicMock(),
            lifecycle_manager=MagicMock(),
            health_monitor=health_mon,
            health_check_interval=0.01,
            max_consecutive_failures=5,
        )

        await coordinator._handle_monitoring_error(RuntimeError("test"))

        health_mon.increment_failures.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_max_failures_reached(self) -> None:
        """Raises error when max failures reached."""
        health_mon = MagicMock()
        health_mon.should_raise_error.return_value = True
        coordinator = HealthCoordinator(
            service_name="test_service",
            state_manager=MagicMock(),
            lifecycle_manager=MagicMock(),
            health_monitor=health_mon,
            health_check_interval=0.01,
            max_consecutive_failures=5,
        )
        error = RuntimeError("test error")

        with pytest.raises(RuntimeError) as exc_info:
            await coordinator._handle_monitoring_error(error)

        assert exc_info.value is error

    @pytest.mark.asyncio
    async def test_sleeps_before_retry(self) -> None:
        """Sleeps before allowing retry."""
        health_mon = MagicMock()
        health_mon.should_raise_error.return_value = False
        coordinator = HealthCoordinator(
            service_name="test_service",
            state_manager=MagicMock(),
            lifecycle_manager=MagicMock(),
            health_monitor=health_mon,
            health_check_interval=0.01,
            max_consecutive_failures=5,
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await coordinator._handle_monitoring_error(RuntimeError("test"))

        mock_sleep.assert_called_once_with(0.01)
