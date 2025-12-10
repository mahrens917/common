"""Unit tests for process_resource_tracker."""

from unittest.mock import Mock, patch

import psutil
import pytest

from common.optimized_status_reporter_helpers.process_resource_tracker import (
    ProcessResourceTracker,
)


class TestProcessResourceTracker:
    """Tests for ProcessResourceTracker."""

    @pytest.fixture
    def mock_process_manager(self):
        """Mock process manager with process_info."""
        pm = Mock()
        pm.process_info = {}
        return pm

    @pytest.fixture
    def tracker(self, mock_process_manager):
        """ProcessResourceTracker instance with mocked dependencies."""
        return ProcessResourceTracker(mock_process_manager)

    def test_get_process_resource_usage_no_service_info(self, tracker):
        """Test returns empty string if no service info."""
        assert tracker.get_process_resource_usage("non_existent_service") == ""

    def test_get_process_resource_usage_no_pid(self, tracker, mock_process_manager):
        """Test returns empty string if service info has no PID."""
        mock_process_manager.process_info["service_A"] = Mock(pid=None)
        assert tracker.get_process_resource_usage("service_A") == ""

    @patch("psutil.Process")
    def test_get_process_resource_usage_success(
        self, mock_psutil_process, tracker, mock_process_manager
    ):
        """Test returns formatted RAM usage on success."""
        mock_process_manager.process_info["service_A"] = Mock(pid=123)

        mock_process_instance = Mock()
        mock_process_instance.memory_percent.return_value = 1.845
        mock_psutil_process.return_value = mock_process_instance

        result = tracker.get_process_resource_usage("service_A")

        mock_psutil_process.assert_called_once_with(123)
        mock_process_instance.memory_percent.assert_called_once()
        assert result == " RAM: 1.8%"

    @pytest.mark.parametrize(
        "exception_class",
        [
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            psutil.Error,
            RuntimeError,
        ],
    )
    @patch("psutil.Process")
    def test_get_process_resource_usage_handles_exceptions(
        self, mock_psutil_process, exception_class, tracker, mock_process_manager
    ):
        """Test returns empty string when psutil.Process raises exceptions."""
        mock_process_manager.process_info["service_A"] = Mock(pid=123)
        mock_psutil_process.side_effect = exception_class("Test exception")

        result = tracker.get_process_resource_usage("service_A")

        mock_psutil_process.assert_called_once_with(123)
        assert result == ""
