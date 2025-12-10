"""Unit tests for process_rediscoverer."""

from unittest.mock import Mock

import pytest

from common.optimized_status_reporter_helpers.service_state_collector_helpers.process_rediscoverer import (
    ProcessRediscoverer,
)


class TestProcessRediscoverer:
    """Tests for ProcessRediscoverer."""

    @pytest.fixture
    def mock_process_manager(self):
        """Mock process manager with _rediscover_process and process_info."""
        pm = Mock()
        pm._rediscover_process = Mock()
        pm.process_info = {}  # Start with empty info
        return pm

    @pytest.fixture
    def mock_pid_validator(self):
        """Mock PID validator."""
        return Mock()

    def test_rediscover_and_validate_no_info(self, mock_process_manager, mock_pid_validator):
        """Test returns False if no process info found after rediscover."""
        service_name = "test_service"
        # process_manager.process_info will remain empty, so info will be None

        is_running, info = ProcessRediscoverer.rediscover_and_validate(
            service_name, mock_process_manager, mock_pid_validator
        )

        mock_process_manager._rediscover_process.assert_called_once_with(service_name)
        assert is_running is False
        assert info is None
        mock_pid_validator.is_running.assert_not_called()

    def test_rediscover_and_validate_info_no_pid(self, mock_process_manager, mock_pid_validator):
        """Test returns False if process info has no PID."""
        service_name = "test_service"
        mock_process_manager.process_info[service_name] = Mock(pid=None)

        is_running, info = ProcessRediscoverer.rediscover_and_validate(
            service_name, mock_process_manager, mock_pid_validator
        )

        mock_process_manager._rediscover_process.assert_called_once_with(service_name)
        assert is_running is False
        assert info.pid is None
        mock_pid_validator.is_running.assert_not_called()

    def test_rediscover_and_validate_pid_validator_running(
        self, mock_process_manager, mock_pid_validator
    ):
        """Test returns True if PID validator indicates process is running."""
        service_name = "test_service"
        mock_process_manager.process_info[service_name] = Mock(pid=123)
        mock_pid_validator.is_running.return_value = True

        is_running, info = ProcessRediscoverer.rediscover_and_validate(
            service_name, mock_process_manager, mock_pid_validator
        )

        mock_process_manager._rediscover_process.assert_called_once_with(service_name)
        mock_pid_validator.is_running.assert_called_once_with(123)
        assert is_running is True
        assert info.pid == 123

    def test_rediscover_and_validate_pid_validator_not_running(
        self, mock_process_manager, mock_pid_validator
    ):
        """Test returns False if PID validator indicates process is not running."""
        service_name = "test_service"
        mock_process_manager.process_info[service_name] = Mock(pid=123)
        mock_pid_validator.is_running.return_value = False

        is_running, info = ProcessRediscoverer.rediscover_and_validate(
            service_name, mock_process_manager, mock_pid_validator
        )

        mock_process_manager._rediscover_process.assert_called_once_with(service_name)
        mock_pid_validator.is_running.assert_called_once_with(123)
        assert is_running is False
        assert info.pid == 123
