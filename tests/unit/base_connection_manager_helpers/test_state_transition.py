"""Tests for state transition module."""

from unittest.mock import MagicMock

from common.base_connection_manager_helpers.state_transition import StateTransitionHandler
from common.connection_state import ConnectionState


class TestStateTransitionHandlerInit:
    """Tests for StateTransitionHandler initialization."""

    def test_initializes_with_dependencies(self) -> None:
        """Initializes with state manager and metrics tracker."""
        state_mgr = MagicMock()
        metrics = MagicMock()

        handler = StateTransitionHandler(state_manager=state_mgr, metrics_tracker=metrics)

        assert handler.state_manager is state_mgr
        assert handler.metrics_tracker is metrics


class TestStateTransitionHandlerTransitionState:
    """Tests for StateTransitionHandler.transition_state."""

    def test_delegates_to_state_manager(self) -> None:
        """Delegates state transition to state manager."""
        state_mgr = MagicMock()
        metrics = MagicMock()

        handler = StateTransitionHandler(state_manager=state_mgr, metrics_tracker=metrics)

        handler.transition_state(ConnectionState.READY)

        state_mgr.transition_state.assert_called_once_with(ConnectionState.READY, None)

    def test_passes_error_context_to_state_manager(self) -> None:
        """Passes error context to state manager."""
        state_mgr = MagicMock()
        metrics = MagicMock()

        handler = StateTransitionHandler(state_manager=state_mgr, metrics_tracker=metrics)

        handler.transition_state(ConnectionState.FAILED, "Connection timeout")

        state_mgr.transition_state.assert_called_once_with(ConnectionState.FAILED, "Connection timeout")

    def test_records_success_on_connected_state(self) -> None:
        """Records success when transitioning to CONNECTED state."""
        state_mgr = MagicMock()
        metrics = MagicMock()

        handler = StateTransitionHandler(state_manager=state_mgr, metrics_tracker=metrics)

        handler.transition_state(ConnectionState.CONNECTED)

        metrics.record_success.assert_called_once()

    def test_records_failure_on_failed_state(self) -> None:
        """Records failure when transitioning to FAILED state."""
        state_mgr = MagicMock()
        metrics = MagicMock()

        handler = StateTransitionHandler(state_manager=state_mgr, metrics_tracker=metrics)

        handler.transition_state(ConnectionState.FAILED)

        metrics.record_failure.assert_called_once()

    def test_does_not_record_metrics_for_other_states(self) -> None:
        """Does not record metrics for non-CONNECTED/FAILED states."""
        state_mgr = MagicMock()
        metrics = MagicMock()

        handler = StateTransitionHandler(state_manager=state_mgr, metrics_tracker=metrics)

        handler.transition_state(ConnectionState.READY)

        metrics.record_success.assert_not_called()
        metrics.record_failure.assert_not_called()

    def test_handles_reconnecting_state(self) -> None:
        """Handles RECONNECTING state without recording metrics."""
        state_mgr = MagicMock()
        metrics = MagicMock()

        handler = StateTransitionHandler(state_manager=state_mgr, metrics_tracker=metrics)

        handler.transition_state(ConnectionState.RECONNECTING, "Lost connection")

        state_mgr.transition_state.assert_called_once()
        metrics.record_success.assert_not_called()
        metrics.record_failure.assert_not_called()

    def test_handles_disconnected_state(self) -> None:
        """Handles DISCONNECTED state without recording metrics."""
        state_mgr = MagicMock()
        metrics = MagicMock()

        handler = StateTransitionHandler(state_manager=state_mgr, metrics_tracker=metrics)

        handler.transition_state(ConnectionState.DISCONNECTED)

        state_mgr.transition_state.assert_called_once()
        metrics.record_success.assert_not_called()
        metrics.record_failure.assert_not_called()
