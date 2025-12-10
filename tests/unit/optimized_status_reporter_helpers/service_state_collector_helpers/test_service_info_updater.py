"""Unit tests for service_info_updater."""

from unittest.mock import Mock

import pytest

from common.monitoring import ProcessStatus
from common.optimized_status_reporter_helpers.service_state_collector_helpers.service_info_updater import (
    ServiceInfoUpdater,
)


class TestServiceInfoUpdater:
    """Tests for ServiceInfoUpdater."""

    @pytest.fixture
    def mock_info(self):
        """Mock process info object."""
        info = Mock()
        info.pid = 123
        info.status = ProcessStatus.STOPPED
        return info

    def test_update_from_handle_pid_differs(self, mock_info):
        """Test pid is updated if different."""
        mock_handle = Mock(pid=456)
        ServiceInfoUpdater.update_from_handle(mock_info, mock_handle)
        assert mock_info.pid == 456

    def test_update_from_handle_pid_same(self, mock_info):
        """Test pid is not updated if same."""
        mock_handle = Mock(pid=123)
        ServiceInfoUpdater.update_from_handle(mock_info, mock_handle)
        assert mock_info.pid == 123

    def test_update_from_handle_status_not_running(self, mock_info):
        """Test status is set to RUNNING if not already."""
        mock_info.status = ProcessStatus.STOPPED
        mock_handle = Mock(pid=123)
        ServiceInfoUpdater.update_from_handle(mock_info, mock_handle)
        assert mock_info.status == ProcessStatus.RUNNING

    def test_update_from_handle_status_running(self, mock_info):
        """Test status remains RUNNING if already."""
        mock_info.status = ProcessStatus.RUNNING
        mock_handle = Mock(pid=123)
        ServiceInfoUpdater.update_from_handle(mock_info, mock_handle)
        assert mock_info.status == ProcessStatus.RUNNING

    def test_clear_stopped_process_status_running(self, mock_info):
        """Test clears pid and sets status to STOPPED if was RUNNING."""
        mock_info.status = ProcessStatus.RUNNING
        ServiceInfoUpdater.clear_stopped_process(mock_info)
        assert mock_info.pid is None
        assert mock_info.status == ProcessStatus.STOPPED

    def test_clear_stopped_process_status_not_running(self, mock_info):
        """Test clears pid but leaves status if not RUNNING."""
        mock_info.status = ProcessStatus.FAILED
        ServiceInfoUpdater.clear_stopped_process(mock_info)
        assert mock_info.pid is None
        assert mock_info.status == ProcessStatus.FAILED

    def test_mark_as_running_info_none(self):
        """Test mark_as_running does nothing if info is None."""
        ServiceInfoUpdater.mark_as_running(None)
        # No assertions needed, just ensure no error

    def test_mark_as_running_status_not_running(self, mock_info):
        """Test status is set to RUNNING if not already."""
        mock_info.status = ProcessStatus.STOPPED
        ServiceInfoUpdater.mark_as_running(mock_info)
        assert mock_info.status == ProcessStatus.RUNNING

    def test_mark_as_running_status_running(self, mock_info):
        """Test status remains RUNNING if already."""
        mock_info.status = ProcessStatus.RUNNING
        ServiceInfoUpdater.mark_as_running(mock_info)
        assert mock_info.status == ProcessStatus.RUNNING
