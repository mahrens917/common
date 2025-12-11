"""Unit tests for StatusManager."""

from functools import partial
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from common.dependency_monitor_helpers.dependency_checker import (
    DependencyConfig,
    DependencyState,
    DependencyStatus,
)
from common.dependency_monitor_helpers.status_manager import StatusManager


@pytest.fixture
def mock_callback_executor():
    """Create a mock callback executor."""
    executor = Mock()
    executor.run_callback = AsyncMock()
    return executor


@pytest.fixture
def mock_telegram_notifier():
    """Create a mock Telegram notifier."""
    return Mock()


@pytest.fixture
def mock_redis_tracker():
    """Create a mock Redis tracker."""
    tracker = Mock()
    tracker.update_dependency_status = AsyncMock()
    return tracker


@pytest.fixture
def dependency_states():
    """Create sample dependency states."""
    redis_config = DependencyConfig(name="redis", check_function=lambda: True, required=True)
    api_config = DependencyConfig(name="api", check_function=lambda: True, required=True)
    optional_config = DependencyConfig(name="optional", check_function=lambda: True, required=False)

    return {
        "redis": DependencyState(config=redis_config, status=DependencyStatus.AVAILABLE),
        "api": DependencyState(config=api_config, status=DependencyStatus.AVAILABLE),
        "optional": DependencyState(config=optional_config, status=DependencyStatus.UNKNOWN),
    }


@pytest.fixture
def status_manager(mock_callback_executor, dependency_states):
    """Create a StatusManager instance."""
    return StatusManager(
        service_name="test_service",
        dependencies=dependency_states,
        callback_executor=mock_callback_executor,
    )


class TestStatusManagerInit:
    """Tests for StatusManager initialization."""

    def test_initialization(self, status_manager, dependency_states, mock_callback_executor):
        """Test StatusManager initializes correctly."""
        assert status_manager.service_name == "test_service"
        assert status_manager.dependencies == dependency_states
        assert status_manager.callback_executor == mock_callback_executor
        assert status_manager.telegram_notifier is None
        assert status_manager.redis_tracker is None
        assert status_manager._recovery_callbacks == []
        assert status_manager._failure_callbacks == []
        assert status_manager._has_been_available is False
        assert status_manager._is_currently_available is False

    def test_initialization_with_telegram(self, mock_callback_executor, mock_telegram_notifier, dependency_states):
        """Test initialization with Telegram notifier."""
        manager = StatusManager(
            service_name="test_service",
            dependencies=dependency_states,
            callback_executor=mock_callback_executor,
            telegram_notifier=mock_telegram_notifier,
        )
        assert manager.telegram_notifier == mock_telegram_notifier

    def test_initialization_with_redis_tracker(self, mock_callback_executor, mock_redis_tracker, dependency_states):
        """Test initialization with Redis tracker."""
        manager = StatusManager(
            service_name="test_service",
            dependencies=dependency_states,
            callback_executor=mock_callback_executor,
            redis_tracker=mock_redis_tracker,
        )
        assert manager.redis_tracker == mock_redis_tracker


class TestCallbackRegistration:
    """Tests for callback registration methods."""

    def test_add_recovery_callback(self, status_manager):
        """Test adding recovery callback."""
        callback = Mock()
        status_manager.add_recovery_callback(callback)
        assert callback in status_manager._recovery_callbacks

    def test_add_multiple_recovery_callbacks(self, status_manager):
        """Test adding multiple recovery callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        status_manager.add_recovery_callback(callback1)
        status_manager.add_recovery_callback(callback2)
        assert len(status_manager._recovery_callbacks) == 2
        assert callback1 in status_manager._recovery_callbacks
        assert callback2 in status_manager._recovery_callbacks

    def test_add_failure_callback(self, status_manager):
        """Test adding failure callback."""
        callback = Mock()
        status_manager.add_failure_callback(callback)
        assert callback in status_manager._failure_callbacks

    def test_add_multiple_failure_callbacks(self, status_manager):
        """Test adding multiple failure callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        status_manager.add_failure_callback(callback1)
        status_manager.add_failure_callback(callback2)
        assert len(status_manager._failure_callbacks) == 2
        assert callback1 in status_manager._failure_callbacks
        assert callback2 in status_manager._failure_callbacks


class TestRequiredDependenciesCheck:
    """Tests for are_required_dependencies_available method."""

    def test_all_required_available(self, status_manager):
        """Test when all required dependencies are available."""
        result = status_manager.are_required_dependencies_available()
        assert result is True

    def test_one_required_unavailable(self, status_manager, dependency_states):
        """Test when one required dependency is unavailable."""
        dependency_states["redis"].status = DependencyStatus.UNAVAILABLE
        result = status_manager.are_required_dependencies_available()
        assert result is False

    def test_optional_unavailable_does_not_affect(self, status_manager, dependency_states):
        """Test that optional dependency status doesn't affect result."""
        dependency_states["optional"].status = DependencyStatus.UNAVAILABLE
        result = status_manager.are_required_dependencies_available()
        assert result is True

    def test_all_required_unknown(self, status_manager, dependency_states):
        """Test when all required dependencies are unknown."""
        dependency_states["redis"].status = DependencyStatus.UNKNOWN
        dependency_states["api"].status = DependencyStatus.UNKNOWN
        result = status_manager.are_required_dependencies_available()
        assert result is False

    def test_empty_dependencies(self, mock_callback_executor):
        """Test with no dependencies."""
        manager = StatusManager(
            service_name="test_service",
            dependencies={},
            callback_executor=mock_callback_executor,
        )
        result = manager.are_required_dependencies_available()
        assert result is True


class TestHandleStatusChanges:
    """Tests for handle_status_changes method."""

    @pytest.mark.asyncio
    async def test_initial_startup_all_available(self, status_manager):
        """Test initial startup when all dependencies are available."""
        await status_manager.handle_status_changes()

        assert status_manager._is_currently_available is True
        assert status_manager._has_been_available is True
        assert status_manager.callback_executor.run_callback.call_count == 0

    @pytest.mark.asyncio
    async def test_initial_startup_dependencies_unavailable(self, status_manager, dependency_states):
        """Test initial startup when dependencies are unavailable."""
        dependency_states["redis"].status = DependencyStatus.UNAVAILABLE

        await status_manager.handle_status_changes()

        assert status_manager._is_currently_available is False
        assert status_manager._has_been_available is False
        assert status_manager.callback_executor.run_callback.call_count == 0

    @pytest.mark.asyncio
    async def test_recovery_triggers_callbacks(self, status_manager, dependency_states):
        """Test that recovery from failure triggers recovery callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        status_manager.add_recovery_callback(callback1)
        status_manager.add_recovery_callback(callback2)

        # Simulate initial failure
        dependency_states["redis"].status = DependencyStatus.UNAVAILABLE
        await status_manager.handle_status_changes()
        assert status_manager._is_currently_available is False

        # Simulate recovery
        status_manager._has_been_available = True
        dependency_states["redis"].status = DependencyStatus.AVAILABLE
        await status_manager.handle_status_changes()

        assert status_manager._is_currently_available is True
        assert status_manager.callback_executor.run_callback.call_count == 2

    @pytest.mark.asyncio
    async def test_failure_triggers_callbacks(self, status_manager, dependency_states):
        """Test that failure triggers failure callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        status_manager.add_failure_callback(callback1)
        status_manager.add_failure_callback(callback2)

        # Simulate initial availability
        await status_manager.handle_status_changes()
        assert status_manager._is_currently_available is True

        # Simulate failure
        dependency_states["redis"].status = DependencyStatus.UNAVAILABLE
        await status_manager.handle_status_changes()

        assert status_manager._is_currently_available is False
        assert status_manager.callback_executor.run_callback.call_count == 2

    @pytest.mark.asyncio
    async def test_no_callbacks_when_status_unchanged(self, status_manager):
        """Test that no callbacks are triggered when status doesn't change."""
        callback = Mock()
        status_manager.add_recovery_callback(callback)
        status_manager.add_failure_callback(callback)

        # First check
        await status_manager.handle_status_changes()

        # Second check with same status
        await status_manager.handle_status_changes()

        # Should only be called once (or zero times depending on initial state)
        assert status_manager.callback_executor.run_callback.call_count == 0

    @pytest.mark.asyncio
    async def test_recovery_without_has_been_available(self, status_manager, dependency_states):
        """Test recovery scenario when service was never available before."""
        # Start with unavailable dependencies
        dependency_states["redis"].status = DependencyStatus.UNAVAILABLE
        status_manager._is_currently_available = False
        status_manager._has_been_available = False

        callback = Mock()
        status_manager.add_recovery_callback(callback)

        # Now make available
        dependency_states["redis"].status = DependencyStatus.AVAILABLE
        await status_manager.handle_status_changes()

        # Should not trigger recovery callbacks (first time available)
        assert status_manager.callback_executor.run_callback.call_count == 0
        assert status_manager._has_been_available is True


class TestRunCallbacks:
    """Tests for _run_callbacks method."""

    @pytest.mark.asyncio
    async def test_run_single_callback(self, status_manager):
        """Test running a single callback."""
        callback = Mock()
        status_manager.callback_executor.run_callback.return_value = None

        await status_manager._run_callbacks([callback])

        status_manager.callback_executor.run_callback.assert_called_once_with(callback)

    @pytest.mark.asyncio
    async def test_run_multiple_callbacks(self, status_manager):
        """Test running multiple callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()
        status_manager.callback_executor.run_callback.return_value = None

        await status_manager._run_callbacks([callback1, callback2, callback3])

        assert status_manager.callback_executor.run_callback.call_count == 3

    @pytest.mark.asyncio
    async def test_callback_error_logged_but_continues(self, status_manager):
        """Test that callback errors are logged but don't stop execution."""
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        # Make second callback fail
        error = Exception("Callback error")
        status_manager.callback_executor.run_callback.side_effect = [None, error, None]

        # Should not raise
        await status_manager._run_callbacks([callback1, callback2, callback3])

        assert status_manager.callback_executor.run_callback.call_count == 3

    @pytest.mark.asyncio
    async def test_run_empty_callbacks_list(self, status_manager):
        """Test running empty callbacks list."""
        await status_manager._run_callbacks([])

        status_manager.callback_executor.run_callback.assert_not_called()


class TestNotifyStatusChange:
    """Tests for notify_status_change method."""

    @pytest.mark.asyncio
    async def test_notify_with_redis_tracker(self, mock_callback_executor, mock_redis_tracker, dependency_states):
        """Test notification with Redis tracker."""
        manager = StatusManager(
            service_name="test_service",
            dependencies=dependency_states,
            callback_executor=mock_callback_executor,
            redis_tracker=mock_redis_tracker,
        )

        await manager.notify_status_change("redis", DependencyStatus.AVAILABLE, DependencyStatus.UNAVAILABLE)

        mock_redis_tracker.update_dependency_status.assert_called_once_with("redis", DependencyStatus.UNAVAILABLE)

    @pytest.mark.asyncio
    async def test_notify_without_redis_tracker(self, status_manager):
        """Test notification without Redis tracker (should not raise)."""
        await status_manager.notify_status_change("redis", DependencyStatus.AVAILABLE, DependencyStatus.UNAVAILABLE)

        # Should complete without error

    @pytest.mark.asyncio
    async def test_notify_unknown_status_skips_telegram(self, mock_callback_executor, mock_telegram_notifier, dependency_states):
        """Test that UNKNOWN old status doesn't send Telegram notification."""
        manager = StatusManager(
            service_name="test_service",
            dependencies=dependency_states,
            callback_executor=mock_callback_executor,
            telegram_notifier=mock_telegram_notifier,
        )

        await manager.notify_status_change("redis", DependencyStatus.UNKNOWN, DependencyStatus.AVAILABLE)

        # Should not call telegram notifier
        mock_callback_executor.run_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_with_telegram_available(self, mock_callback_executor, mock_telegram_notifier, dependency_states):
        """Test Telegram notification for dependency becoming available."""
        manager = StatusManager(
            service_name="test_service",
            dependencies=dependency_states,
            callback_executor=mock_callback_executor,
            telegram_notifier=mock_telegram_notifier,
        )
        mock_callback_executor.run_callback.return_value = None

        await manager.notify_status_change("redis", DependencyStatus.UNAVAILABLE, DependencyStatus.AVAILABLE)

        # Should call telegram notifier with partial
        assert mock_callback_executor.run_callback.call_count == 1
        call_args = mock_callback_executor.run_callback.call_args[0][0]
        assert isinstance(call_args, partial)

    @pytest.mark.asyncio
    async def test_notify_with_telegram_unavailable(self, mock_callback_executor, mock_telegram_notifier, dependency_states):
        """Test Telegram notification for dependency becoming unavailable."""
        manager = StatusManager(
            service_name="test_service",
            dependencies=dependency_states,
            callback_executor=mock_callback_executor,
            telegram_notifier=mock_telegram_notifier,
        )
        mock_callback_executor.run_callback.return_value = None

        await manager.notify_status_change("redis", DependencyStatus.AVAILABLE, DependencyStatus.UNAVAILABLE)

        # Should call telegram notifier
        assert mock_callback_executor.run_callback.call_count == 1

    @pytest.mark.asyncio
    async def test_notify_telegram_error_logged(self, mock_callback_executor, mock_telegram_notifier, dependency_states):
        """Test that Telegram notification errors are logged."""
        manager = StatusManager(
            service_name="test_service",
            dependencies=dependency_states,
            callback_executor=mock_callback_executor,
            telegram_notifier=mock_telegram_notifier,
        )

        error = Exception("Telegram send failed")
        mock_callback_executor.run_callback.return_value = error

        # Should not raise
        await manager.notify_status_change("redis", DependencyStatus.AVAILABLE, DependencyStatus.UNAVAILABLE)

    @pytest.mark.asyncio
    async def test_notify_message_format_available(self, mock_callback_executor, mock_telegram_notifier, dependency_states):
        """Test message format for available status."""
        manager = StatusManager(
            service_name="test_service",
            dependencies=dependency_states,
            callback_executor=mock_callback_executor,
            telegram_notifier=mock_telegram_notifier,
        )
        mock_callback_executor.run_callback.return_value = None

        await manager.notify_status_change("redis", DependencyStatus.UNAVAILABLE, DependencyStatus.AVAILABLE)

        # Check that the message is created correctly
        call_args = mock_callback_executor.run_callback.call_args[0][0]
        assert isinstance(call_args, partial)

    @pytest.mark.asyncio
    async def test_notify_without_telegram(self, status_manager):
        """Test notification without Telegram notifier (should not raise)."""
        await status_manager.notify_status_change("redis", DependencyStatus.AVAILABLE, DependencyStatus.UNAVAILABLE)

        # Should complete without error


class TestStatusManagerIntegration:
    """Integration tests for StatusManager."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_callbacks(self, mock_callback_executor, dependency_states):
        """Test full lifecycle with failure and recovery."""
        recovery_callback = Mock()
        failure_callback = Mock()

        manager = StatusManager(
            service_name="test_service",
            dependencies=dependency_states,
            callback_executor=mock_callback_executor,
        )
        manager.add_recovery_callback(recovery_callback)
        manager.add_failure_callback(failure_callback)

        mock_callback_executor.run_callback.return_value = None

        # Initial startup - all available
        await manager.handle_status_changes()
        assert manager._is_currently_available is True
        assert manager._has_been_available is True

        # Dependency fails
        dependency_states["redis"].status = DependencyStatus.UNAVAILABLE
        await manager.handle_status_changes()
        assert manager._is_currently_available is False
        assert mock_callback_executor.run_callback.call_count == 1

        # Dependency recovers
        dependency_states["redis"].status = DependencyStatus.AVAILABLE
        await manager.handle_status_changes()
        assert manager._is_currently_available is True
        assert mock_callback_executor.run_callback.call_count == 2

    @pytest.mark.asyncio
    async def test_optional_dependencies_do_not_trigger_callbacks(self, mock_callback_executor, dependency_states):
        """Test that optional dependencies don't trigger failure callbacks."""
        failure_callback = Mock()

        manager = StatusManager(
            service_name="test_service",
            dependencies=dependency_states,
            callback_executor=mock_callback_executor,
        )
        manager.add_failure_callback(failure_callback)

        # Initial startup
        await manager.handle_status_changes()

        # Optional dependency fails (should not trigger callbacks)
        dependency_states["optional"].status = DependencyStatus.UNAVAILABLE
        await manager.handle_status_changes()

        # Failure callback should not have been called
        mock_callback_executor.run_callback.assert_not_called()
