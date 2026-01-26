"""Unit tests for service_info_updater.

NOTE: All ServiceInfoUpdater methods are intentionally no-ops.
ProcessInfo should only be modified by ProcessManager via psutil probing,
not by status reporters. These tests verify the no-op behavior.
"""

from unittest.mock import Mock

import pytest

from common.monitoring import ProcessStatus
from common.optimized_status_reporter_helpers.service_state_collector_helpers.service_info_updater import (
    ServiceInfoUpdater,
)


class TestServiceInfoUpdater:
    """Tests for ServiceInfoUpdater.

    All methods are no-ops to avoid race conditions with ProcessManager.
    """

    @pytest.fixture
    def mock_info(self):
        """Mock process info object."""
        info = Mock()
        info.pid = 123
        info.status = ProcessStatus.STOPPED
        return info

    def test_update_from_handle_does_not_modify_pid(self, mock_info):
        """Test pid is NOT modified (method is no-op)."""
        mock_handle = Mock(pid=456)
        ServiceInfoUpdater.update_from_handle(mock_info, mock_handle)
        assert mock_info.pid == 123  # Unchanged

    def test_update_from_handle_does_not_modify_status(self, mock_info):
        """Test status is NOT modified (method is no-op)."""
        mock_info.status = ProcessStatus.STOPPED
        mock_handle = Mock(pid=123)
        ServiceInfoUpdater.update_from_handle(mock_info, mock_handle)
        assert mock_info.status == ProcessStatus.STOPPED  # Unchanged

    def test_clear_stopped_process_does_not_modify_pid(self, mock_info):
        """Test pid is NOT modified (method is no-op)."""
        mock_info.status = ProcessStatus.RUNNING
        ServiceInfoUpdater.clear_stopped_process(mock_info)
        assert mock_info.pid == 123  # Unchanged

    def test_clear_stopped_process_does_not_modify_status(self, mock_info):
        """Test status is NOT modified (method is no-op)."""
        mock_info.status = ProcessStatus.RUNNING
        ServiceInfoUpdater.clear_stopped_process(mock_info)
        assert mock_info.status == ProcessStatus.RUNNING  # Unchanged

    def test_mark_as_running_info_none(self):
        """Test mark_as_running does nothing if info is None."""
        ServiceInfoUpdater.mark_as_running(None)
        # No assertions needed, just ensure no error

    def test_mark_as_running_does_not_modify_status(self, mock_info):
        """Test status is NOT modified (method is no-op)."""
        mock_info.status = ProcessStatus.STOPPED
        ServiceInfoUpdater.mark_as_running(mock_info)
        assert mock_info.status == ProcessStatus.STOPPED  # Unchanged
