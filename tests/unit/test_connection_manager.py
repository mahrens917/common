"""Tests for connection_manager module."""

from unittest.mock import MagicMock

from common.connection_manager import BaseConnectionManager, ConnectionLifecycleMixin
from common.connection_state import ConnectionState
from common.health.types import HealthCheckResult


class ConcreteConnectionManager(BaseConnectionManager):
    """Concrete implementation for testing."""

    async def establish_connection(self) -> bool:
        """Establish connection."""
        return True

    async def check_connection_health(self) -> HealthCheckResult:
        """Check health."""
        return HealthCheckResult(is_healthy=True, details="OK")

    async def cleanup_connection(self) -> None:
        """Cleanup."""
        pass


def test_connection_lifecycle_mixin_properties():
    """Test ConnectionLifecycleMixin property setters."""
    mixin = ConnectionLifecycleMixin()

    # Test _health_check_task property
    task = MagicMock()
    mixin.health_check_task_handle = None
    mixin._health_check_task = task
    assert mixin._health_check_task == task
    assert mixin.health_check_task_handle == task

    # Test _reconnection_task property
    reconnect_task = MagicMock()
    mixin.reconnection_task_handle = None
    mixin._reconnection_task = reconnect_task
    assert mixin._reconnection_task == reconnect_task
    assert mixin.reconnection_task_handle == reconnect_task

    # Test _shutdown_requested property
    mixin.shutdown_requested_flag = False
    mixin._shutdown_requested = True
    assert mixin._shutdown_requested is True
    assert mixin.shutdown_requested_flag is True


def test_connection_lifecycle_mixin_state_property():
    """Test state property getter and setter."""
    mixin = ConnectionLifecycleMixin()
    mixin.state_manager = MagicMock()
    mixin.state_manager.state = ConnectionState.DISCONNECTED

    # Test getter
    assert mixin.state == ConnectionState.DISCONNECTED

    # Test setter
    mixin.state = ConnectionState.CONNECTED
    assert mixin.state_manager.state == ConnectionState.CONNECTED


def test_base_connection_manager_init_with_alerter():
    """Test BaseConnectionManager initialization with custom alerter."""
    alerter = MagicMock()
    manager = ConcreteConnectionManager("test_service", alerter)
    assert manager.alerter is alerter
    assert manager.service_name == "test_service"


def test_base_connection_manager_transition_state():
    """Test transition_state method."""
    manager = ConcreteConnectionManager("test_service")
    manager.state_transition_handler.transition_state = MagicMock()
    manager.metrics_tracker.get_metrics = MagicMock(return_value={"transitions": 1})

    manager.transition_state(ConnectionState.CONNECTED, "success")

    manager.state_transition_handler.transition_state.assert_called_once_with(ConnectionState.CONNECTED, "success")
    assert manager.metrics == {"transitions": 1}
