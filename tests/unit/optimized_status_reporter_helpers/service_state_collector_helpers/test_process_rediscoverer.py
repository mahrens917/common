"""Unit tests for rediscover_and_validate."""

from unittest.mock import Mock, patch

import pytest

from common.optimized_status_reporter_helpers.service_state_collector import (
    rediscover_and_validate,
)


class TestProcessRediscoverer:
    """Tests for rediscover_and_validate."""

    @pytest.fixture
    def mock_process_manager(self):
        pm = Mock()
        pm._rediscover_process = Mock()
        pm.process_info = {}
        return pm

    def test_rediscover_and_validate_no_info(self, mock_process_manager):
        """Returns False if no process info found after rediscover."""
        is_proc_running, info = rediscover_and_validate("test_service", mock_process_manager)

        mock_process_manager._rediscover_process.assert_called_once_with("test_service")
        assert is_proc_running is False
        assert info is None

    def test_rediscover_and_validate_info_no_pid(self, mock_process_manager):
        """Returns False if process info has no PID."""
        mock_process_manager.process_info["test_service"] = Mock(pid=None)

        is_proc_running, info = rediscover_and_validate("test_service", mock_process_manager)

        mock_process_manager._rediscover_process.assert_called_once_with("test_service")
        assert is_proc_running is False
        assert info.pid is None

    def test_rediscover_and_validate_pid_running(self, mock_process_manager):
        """Returns True if PID validator indicates process is running."""
        mock_process_manager.process_info["test_service"] = Mock(pid=123)

        with patch("common.optimized_status_reporter_helpers.service_state_collector.is_running", return_value=True):
            is_proc_running, info = rediscover_and_validate("test_service", mock_process_manager)

        mock_process_manager._rediscover_process.assert_called_once_with("test_service")
        assert is_proc_running is True
        assert info.pid == 123

    def test_rediscover_and_validate_pid_not_running(self, mock_process_manager):
        """Returns False if PID validator indicates process is not running."""
        mock_process_manager.process_info["test_service"] = Mock(pid=123)

        with patch("common.optimized_status_reporter_helpers.service_state_collector.is_running", return_value=False):
            is_proc_running, info = rediscover_and_validate("test_service", mock_process_manager)

        mock_process_manager._rediscover_process.assert_called_once_with("test_service")
        assert is_proc_running is False
        assert info.pid == 123
