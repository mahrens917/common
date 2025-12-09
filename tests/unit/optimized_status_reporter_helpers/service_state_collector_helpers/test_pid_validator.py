"""Unit tests for pid_validator."""

from unittest.mock import Mock, patch

import psutil
import pytest

from src.common.optimized_status_reporter_helpers.service_state_collector_helpers.pid_validator import (
    PidValidator,
)


class TestPidValidator:
    """Tests for PidValidator."""

    @patch("psutil.Process")
    def test_is_running_and_not_zombie(self, mock_psutil_process):
        """Test is_running returns True for running, non-zombie process."""
        mock_process_instance = Mock()
        mock_process_instance.is_running.return_value = True
        mock_process_instance.status.return_value = psutil.STATUS_RUNNING
        mock_psutil_process.return_value = mock_process_instance

        assert PidValidator.is_running(123) is True
        mock_psutil_process.assert_called_once_with(123)
        mock_process_instance.is_running.assert_called_once()
        mock_process_instance.status.assert_called_once()

    @patch("psutil.Process")
    def test_is_running_but_zombie(self, mock_psutil_process):
        """Test is_running returns False for running but zombie process."""
        mock_process_instance = Mock()
        mock_process_instance.is_running.return_value = True
        mock_process_instance.status.return_value = psutil.STATUS_ZOMBIE
        mock_psutil_process.return_value = mock_process_instance

        assert PidValidator.is_running(123) is False
        mock_psutil_process.assert_called_once_with(123)
        mock_process_instance.is_running.assert_called_once()
        mock_process_instance.status.assert_called_once()

    @patch("psutil.Process")
    def test_is_not_running(self, mock_psutil_process):
        """Test is_running returns False for not running process."""
        mock_process_instance = Mock()
        mock_process_instance.is_running.return_value = False
        mock_process_instance.status.return_value = (
            psutil.STATUS_RUNNING
        )  # Status shouldn't matter if not running
        mock_psutil_process.return_value = mock_process_instance

        assert PidValidator.is_running(123) is False
        mock_psutil_process.assert_called_once_with(123)
        mock_process_instance.is_running.assert_called_once()
        mock_process_instance.status.assert_not_called()  # status() should not be called if is_running() is False

    @pytest.mark.parametrize(
        "exception_class",
        [
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ],
    )
    @patch("psutil.Process")
    def test_is_running_handles_exceptions(self, mock_psutil_process, exception_class):
        """Test is_running returns False when psutil.Process raises exceptions."""
        mock_psutil_process.side_effect = exception_class("Test exception")

        assert PidValidator.is_running(123) is False
        mock_psutil_process.assert_called_once_with(123)
