"""Tests for state manager module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.base_connection_manager_helpers.state_manager import ConnectionStateManager
from common.connection_state import ConnectionState


class TestConnectionStateManagerInit:
    """Tests for ConnectionStateManager initialization."""

    def test_initializes_with_service_name(self) -> None:
        """Initializes with service name."""
        manager = ConnectionStateManager(service_name="test_service")

        assert manager.service_name == "test_service"
        assert manager.state == ConnectionState.DISCONNECTED
        assert manager.state_tracker is None

    def test_initializes_state_change_time(self) -> None:
        """Initializes state change time."""
        manager = ConnectionStateManager(service_name="test_service")

        assert manager.state_change_time > 0


class TestConnectionStateManagerTransitionState:
    """Tests for ConnectionStateManager.transition_state."""

    def test_transitions_to_new_state(self) -> None:
        """Transitions to new state."""
        manager = ConnectionStateManager(service_name="test_service")

        with patch("common.base_connection_manager_helpers.state_manager.safely_schedule_coroutine"):
            manager.transition_state(ConnectionState.READY)

        assert manager.state == ConnectionState.READY

    def test_updates_state_change_time(self) -> None:
        """Updates state change time on transition."""
        manager = ConnectionStateManager(service_name="test_service")
        initial_time = manager.state_change_time

        with patch("common.base_connection_manager_helpers.state_manager.safely_schedule_coroutine"):
            with patch("time.time", return_value=initial_time + 10):
                manager.transition_state(ConnectionState.READY)

        assert manager.state_change_time == initial_time + 10

    def test_creates_broadcast_task_on_state_change(self) -> None:
        """Creates broadcast task on state change."""
        manager = ConnectionStateManager(service_name="test_service")

        with patch("common.base_connection_manager_helpers.state_manager.safely_schedule_coroutine") as mock_schedule:
            manager.transition_state(ConnectionState.READY)

        mock_schedule.assert_called_once()

    def test_does_not_transition_if_same_state(self) -> None:
        """Does not transition if same state."""
        manager = ConnectionStateManager(service_name="test_service")
        # Initial state is DISCONNECTED

        with patch("common.base_connection_manager_helpers.state_manager.safely_schedule_coroutine") as mock_schedule:
            manager.transition_state(ConnectionState.DISCONNECTED)

        mock_schedule.assert_not_called()

    def test_logs_state_transition(self) -> None:
        """Logs state transition."""
        manager = ConnectionStateManager(service_name="test_service")

        with patch("common.base_connection_manager_helpers.state_manager.safely_schedule_coroutine"):
            with patch.object(manager.logger, "info") as mock_log:
                manager.transition_state(ConnectionState.READY)

        mock_log.assert_called_once()
        # Uses lowercase enum values
        assert "disconnected" in mock_log.call_args[0][0]
        assert "ready" in mock_log.call_args[0][0]


class TestConnectionStateManagerInitializeStateTracker:
    """Tests for ConnectionStateManager._initialize_state_tracker."""

    @pytest.mark.asyncio
    async def test_initializes_state_tracker(self) -> None:
        """Initializes state tracker."""
        manager = ConnectionStateManager(service_name="test_service")
        mock_tracker = MagicMock()

        with patch(
            "common.base_connection_manager_helpers.state_manager.get_connection_state_tracker",
            new_callable=AsyncMock,
            return_value=mock_tracker,
        ):
            await manager._initialize_state_tracker()

        assert manager.state_tracker is mock_tracker

    @pytest.mark.asyncio
    async def test_does_not_reinitialize_if_already_set(self) -> None:
        """Does not reinitialize if already set."""
        manager = ConnectionStateManager(service_name="test_service")
        mock_tracker = MagicMock()
        manager.state_tracker = mock_tracker

        with patch(
            "common.base_connection_manager_helpers.state_manager.get_connection_state_tracker",
            new_callable=AsyncMock,
        ) as mock_get:
            await manager._initialize_state_tracker()

        mock_get.assert_not_called()
        assert manager.state_tracker is mock_tracker


class TestConnectionStateManagerBroadcastStateChange:
    """Tests for ConnectionStateManager._broadcast_state_change."""

    @pytest.mark.asyncio
    async def test_initializes_tracker_if_none(self) -> None:
        """Initializes tracker if none."""
        manager = ConnectionStateManager(service_name="test_service")
        mock_tracker = MagicMock()
        mock_tracker.update_connection_state = AsyncMock()

        with patch(
            "common.base_connection_manager_helpers.state_manager.get_connection_state_tracker",
            new_callable=AsyncMock,
            return_value=mock_tracker,
        ):
            await manager._broadcast_state_change(ConnectionState.READY)

        assert manager.state_tracker is mock_tracker

    @pytest.mark.asyncio
    async def test_updates_connection_state(self) -> None:
        """Updates connection state via tracker."""
        manager = ConnectionStateManager(service_name="test_service")
        mock_tracker = MagicMock()
        mock_tracker.update_connection_state = AsyncMock()
        manager.state_tracker = mock_tracker

        await manager._broadcast_state_change(ConnectionState.READY, "context")

        mock_tracker.update_connection_state.assert_called_once_with(
            service_name="test_service",
            state=ConnectionState.READY,
            error_context="context",
            consecutive_failures=0,
        )

    @pytest.mark.asyncio
    async def test_handles_none_tracker(self) -> None:
        """Handles case where tracker initialization fails."""
        manager = ConnectionStateManager(service_name="test_service")

        with patch(
            "common.base_connection_manager_helpers.state_manager.get_connection_state_tracker",
            new_callable=AsyncMock,
            return_value=None,
        ):
            # Should not raise
            await manager._broadcast_state_change(ConnectionState.READY)


class TestConnectionStateManagerGetState:
    """Tests for ConnectionStateManager.get_state."""

    def test_returns_current_state(self) -> None:
        """Returns current state."""
        manager = ConnectionStateManager(service_name="test_service")

        assert manager.get_state() == ConnectionState.DISCONNECTED

    def test_returns_updated_state(self) -> None:
        """Returns updated state after transition."""
        manager = ConnectionStateManager(service_name="test_service")

        with patch("common.base_connection_manager_helpers.state_manager.safely_schedule_coroutine"):
            manager.transition_state(ConnectionState.READY)

        assert manager.get_state() == ConnectionState.READY


class TestConnectionStateManagerGetStateDuration:
    """Tests for ConnectionStateManager.get_state_duration."""

    def test_returns_time_in_current_state(self) -> None:
        """Returns time in current state."""
        manager = ConnectionStateManager(service_name="test_service")

        with patch("time.time", return_value=manager.state_change_time + 5):
            duration = manager.get_state_duration()

        assert duration == 5

    def test_returns_zero_initially(self) -> None:
        """Returns approximately zero initially."""
        manager = ConnectionStateManager(service_name="test_service")

        duration = manager.get_state_duration()

        # Should be very small (just initialized)
        assert duration >= 0
        assert duration < 1
