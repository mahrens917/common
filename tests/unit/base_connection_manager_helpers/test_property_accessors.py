"""Tests for PropertyAccessorsMixin."""

from unittest.mock import Mock

import pytest

from common.base_connection_manager_helpers.property_accessors import PropertyAccessorsMixin


class TestPropertyAccessorsMixin:
    """Test the property accessors mixin."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context with required attributes."""
        context = Mock(spec=PropertyAccessorsMixin)
        context.state_manager = Mock()
        context.lifecycle_manager = Mock()
        context.health_coordinator = Mock()
        context.health_check_task_handle = None
        context.reconnection_task_handle = None
        context.shutdown_requested_flag = False
        # Apply the mixin methods to the mock
        for attr_name in dir(PropertyAccessorsMixin):
            if not attr_name.startswith("_"):
                attr = getattr(PropertyAccessorsMixin, attr_name)
                if isinstance(attr, property):
                    # For property objects, we need to bind them properly
                    setattr(type(context), attr_name, attr)
        return context

    def test_state_tracker_getter_with_value(self, mock_context):
        """Test getting state_tracker when it exists."""
        mock_context.state_manager.state_tracker = Mock()
        result = PropertyAccessorsMixin.state_tracker.fget(mock_context)
        assert result is mock_context.state_manager.state_tracker

    def test_state_tracker_getter_without_value(self, mock_context):
        """Test getting state_tracker when it doesn't exist."""
        delattr(mock_context.state_manager, "state_tracker")
        result = PropertyAccessorsMixin.state_tracker.fget(mock_context)
        assert result is None

    def test_state_tracker_setter(self, mock_context):
        """Test setting state_tracker."""
        new_value = Mock()
        PropertyAccessorsMixin.state_tracker.fset(mock_context, new_value)
        assert mock_context.state_manager.state_tracker == new_value

    def test_health_check_task_getter(self, mock_context):
        """Test getting health_check_task."""
        test_task = Mock()
        mock_context.health_check_task_handle = test_task
        result = PropertyAccessorsMixin.health_check_task.fget(mock_context)
        assert result is test_task

    def test_health_check_task_setter_with_lifecycle_manager_attribute(self, mock_context):
        """Test setting health_check_task when lifecycle_manager has the attribute."""
        new_task = Mock()
        mock_context.lifecycle_manager.health_check_task = None
        PropertyAccessorsMixin.health_check_task.fset(mock_context, new_task)
        assert mock_context.health_check_task_handle == new_task
        assert mock_context.lifecycle_manager.health_check_task == new_task

    def test_health_check_task_setter_without_lifecycle_manager_attribute(self, mock_context):
        """Test setting health_check_task when lifecycle_manager doesn't have the attribute."""
        new_task = Mock()
        delattr(mock_context.lifecycle_manager, "health_check_task")
        PropertyAccessorsMixin.health_check_task.fset(mock_context, new_task)
        assert mock_context.health_check_task_handle == new_task

    def test_reconnection_task_getter_from_coordinator(self, mock_context):
        """Test getting reconnection_task from health_coordinator."""
        test_task = Mock()
        mock_context.health_coordinator.reconnection_task = test_task
        result = PropertyAccessorsMixin.reconnection_task.fget(mock_context)
        assert result is test_task

    def test_reconnection_task_getter_from_handle(self, mock_context):
        """Test getting reconnection_task from handle when coordinator doesn't have it."""
        test_task = Mock()
        mock_context.reconnection_task_handle = test_task
        delattr(mock_context.health_coordinator, "reconnection_task")
        result = PropertyAccessorsMixin.reconnection_task.fget(mock_context)
        assert result is test_task

    def test_reconnection_task_setter_with_all_attributes(self, mock_context):
        """Test setting reconnection_task when all managers have the attribute."""
        new_task = Mock()
        mock_context.health_coordinator.reconnection_task = None
        mock_context.lifecycle_manager.reconnection_task = None
        PropertyAccessorsMixin.reconnection_task.fset(mock_context, new_task)
        assert mock_context.reconnection_task_handle == new_task
        assert mock_context.health_coordinator.reconnection_task == new_task
        assert mock_context.lifecycle_manager.reconnection_task == new_task

    def test_reconnection_task_setter_without_coordinator_attribute(self, mock_context):
        """Test setting reconnection_task when health_coordinator doesn't have attribute."""
        new_task = Mock()
        delattr(mock_context.health_coordinator, "reconnection_task")
        mock_context.lifecycle_manager.reconnection_task = None
        PropertyAccessorsMixin.reconnection_task.fset(mock_context, new_task)
        assert mock_context.reconnection_task_handle == new_task
        assert mock_context.lifecycle_manager.reconnection_task == new_task

    def test_reconnection_task_setter_without_lifecycle_attribute(self, mock_context):
        """Test setting reconnection_task when lifecycle_manager doesn't have attribute."""
        new_task = Mock()
        mock_context.health_coordinator.reconnection_task = None
        delattr(mock_context.lifecycle_manager, "reconnection_task")
        PropertyAccessorsMixin.reconnection_task.fset(mock_context, new_task)
        assert mock_context.reconnection_task_handle == new_task
        assert mock_context.health_coordinator.reconnection_task == new_task

    def test_shutdown_requested_getter(self, mock_context):
        """Test getting shutdown_requested flag."""
        mock_context.shutdown_requested_flag = True
        result = PropertyAccessorsMixin.shutdown_requested.fget(mock_context)
        assert result is True

    def test_shutdown_requested_setter(self, mock_context):
        """Test setting shutdown_requested flag."""
        PropertyAccessorsMixin.shutdown_requested.fset(mock_context, True)
        assert mock_context.shutdown_requested_flag is True
        assert mock_context.lifecycle_manager.shutdown_requested is True
