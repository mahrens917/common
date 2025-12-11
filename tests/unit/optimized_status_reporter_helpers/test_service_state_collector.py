"""Unit tests for service_state_collector."""

from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest

from common.monitoring import ProcessStatus
from common.optimized_status_reporter_helpers.service_state_collector import (
    ServiceStateCollector,
)


class TestServiceStateCollector:
    """Tests for ServiceStateCollector."""

    @pytest.fixture
    def mock_process_manager(self):
        """Mock process manager with services and process_info."""
        pm = Mock()
        pm.services = ["service_A", "service_B"]

        # Mimic process_info structure, where keys are service names
        # and values are objects with `pid` and `status` attributes.
        # This setup allows for dynamic control of process info during tests.
        class ServiceInfo:
            def __init__(self, pid, status):
                self.pid = pid
                self.status = status

        pm.process_info = {
            "service_A": ServiceInfo(pid=123, status=ProcessStatus.RUNNING),
            "service_B": ServiceInfo(pid=456, status=ProcessStatus.STOPPED),
        }
        pm.processes = {
            "service_A": Mock(poll=Mock(return_value=None)),  # Running
            "service_B": Mock(poll=Mock(return_value=1)),  # Stopped
        }
        return pm

    @pytest.fixture
    def collector(self, mock_process_manager):
        """ServiceStateCollector instance with mocked dependencies."""
        return ServiceStateCollector(mock_process_manager)

    @pytest.mark.asyncio
    async def test_collect_running_services(self, collector):
        """Test collect_running_services identifies running services."""
        # Mock the internal method _check_service_status
        with patch.object(collector, "_check_service_status") as mock_check_service_status:
            mock_check_service_status.side_effect = [
                True,
                False,
            ]  # service_A is running, service_B is not

            running_services = await collector.collect_running_services()

            assert running_services == [{"name": "service_A"}]
            assert mock_check_service_status.call_count == len(collector.process_manager.services)
            mock_check_service_status.assert_any_call(
                "service_A", ANY, ANY, ANY
            )  # PidValidator, ProcessRediscoverer, ServiceInfoUpdater are passed dynamically
            mock_check_service_status.assert_any_call("service_B", ANY, ANY, ANY)

    def test_check_service_status_invalid_status_type(self, collector, mock_process_manager):
        """Test _check_service_status raises TypeError for invalid status type."""

        # Setup invalid status type
        class BadStatus:
            pass

        mock_process_manager.process_info["service_A"].status = BadStatus()

        with pytest.raises(TypeError, match="invalid status type"):
            collector._check_service_status("service_A", Mock(), Mock(), Mock())

    @patch("common.optimized_status_reporter_helpers.service_state_collector.PidValidator")
    @patch("common.optimized_status_reporter_helpers.service_state_collector.ProcessRediscoverer")
    @patch("common.optimized_status_reporter_helpers.service_state_collector.ServiceInfoUpdater")
    @patch.object(ServiceStateCollector, "_check_process_handle")
    def test_check_service_status_process_handle_running(
        self,
        mock_check_process_handle,
        mock_updater,
        mock_rediscoverer,
        mock_pid_validator,
        collector,
        mock_process_manager,
    ):
        """Test _check_service_status returns True when _check_process_handle indicates running."""
        mock_check_process_handle.return_value = True

        is_running = collector._check_service_status("service_A", mock_pid_validator, mock_rediscoverer, mock_updater)

        assert is_running is True
        mock_check_process_handle.assert_called_once_with("service_A", mock_process_manager.process_info["service_A"], mock_updater)
        mock_rediscoverer.rediscover_and_validate.assert_not_called()

    @patch("common.optimized_status_reporter_helpers.service_state_collector.PidValidator")
    @patch("common.optimized_status_reporter_helpers.service_state_collector.ProcessRediscoverer")
    @patch("common.optimized_status_reporter_helpers.service_state_collector.ServiceInfoUpdater")
    @patch.object(ServiceStateCollector, "_check_process_handle")
    def test_check_service_status_rediscoverer_finds_process(
        self,
        mock_check_process_handle,
        mock_updater,
        mock_rediscoverer,
        mock_pid_validator,
        collector,
        mock_process_manager,
    ):
        """Test _check_service_status finds process via rediscoverer."""
        mock_check_process_handle.return_value = False
        mock_rediscoverer.rediscover_and_validate.return_value = (
            True,
            Mock(),
        )  # (is_running, info)

        is_running = collector._check_service_status("service_B", mock_pid_validator, mock_rediscoverer, mock_updater)

        assert is_running is True
        mock_rediscoverer.rediscover_and_validate.assert_called_once()
        mock_updater.mark_as_running.assert_called_once()
        mock_updater.clear_stopped_process.assert_not_called()

    @patch("common.optimized_status_reporter_helpers.service_state_collector.PidValidator")
    @patch("common.optimized_status_reporter_helpers.service_state_collector.ProcessRediscoverer")
    @patch("common.optimized_status_reporter_helpers.service_state_collector.ServiceInfoUpdater")
    @patch.object(ServiceStateCollector, "_check_process_handle")
    def test_check_service_status_rediscoverer_fails_no_info(
        self,
        mock_check_process_handle,
        mock_updater,
        mock_rediscoverer,
        mock_pid_validator,
        collector,
        mock_process_manager,
    ):
        """Test _check_service_status fails via rediscoverer, no info updated."""
        mock_check_process_handle.return_value = False
        mock_rediscoverer.rediscover_and_validate.return_value = (False, None)  # (is_running, info)

        # Ensure service_B has info, then remove it for this test case (no info from rediscoverer)
        del mock_process_manager.process_info["service_B"]

        is_running = collector._check_service_status("service_B", mock_pid_validator, mock_rediscoverer, mock_updater)

        assert is_running is False
        mock_rediscoverer.rediscover_and_validate.assert_called_once()
        mock_updater.mark_as_running.assert_not_called()
        mock_updater.clear_stopped_process.assert_not_called()

    @patch("common.optimized_status_reporter_helpers.service_state_collector.PidValidator")
    @patch("common.optimized_status_reporter_helpers.service_state_collector.ProcessRediscoverer")
    @patch("common.optimized_status_reporter_helpers.service_state_collector.ServiceInfoUpdater")
    @patch.object(ServiceStateCollector, "_check_process_handle")
    def test_check_service_status_rediscoverer_fails_with_info_cleared(
        self,
        mock_check_process_handle,
        mock_updater,
        mock_rediscoverer,
        mock_pid_validator,
        collector,
        mock_process_manager,
    ):
        """Test _check_service_status fails via rediscoverer, process info cleared."""
        mock_check_process_handle.return_value = False
        mock_rediscoverer.rediscover_and_validate.return_value = (
            False,
            Mock(),
        )  # (is_running, info)

        is_running = collector._check_service_status("service_B", mock_pid_validator, mock_rediscoverer, mock_updater)

        assert is_running is False
        mock_rediscoverer.rediscover_and_validate.assert_called_once()
        mock_updater.mark_as_running.assert_not_called()
        mock_updater.clear_stopped_process.assert_called_once()

    @patch("common.optimized_status_reporter_helpers.service_state_collector.ServiceInfoUpdater")
    def test_check_process_handle_no_process_handle(self, mock_updater, collector, mock_process_manager):
        """Test _check_process_handle returns False if no process handle."""
        mock_process_manager.processes = {}  # No processes defined

        is_running = collector._check_process_handle("service_A", Mock(pid=123), mock_updater)
        assert is_running is False
        mock_updater.update_from_handle.assert_not_called()

    @patch("common.optimized_status_reporter_helpers.service_state_collector.ServiceInfoUpdater")
    def test_check_process_handle_process_not_running(self, mock_updater, collector, mock_process_manager):
        """Test _check_process_handle returns False if process is not running."""
        mock_process_manager.processes["service_A"].poll.return_value = 1  # Not None, so process is stopped

        is_running = collector._check_process_handle("service_A", Mock(pid=123), mock_updater)
        assert is_running is False
        mock_updater.update_from_handle.assert_not_called()

    @patch("common.optimized_status_reporter_helpers.service_state_collector.ServiceInfoUpdater")
    def test_check_process_handle_process_running_updates_info(self, mock_updater, collector, mock_process_manager):
        """Test _check_process_handle returns True and updates info if process is running."""
        # mock_process_manager.processes["service_A"].poll.return_value is None by default from fixture
        mock_info = Mock(pid=123)
        mock_process_handle = mock_process_manager.processes["service_A"]

        is_running = collector._check_process_handle("service_A", mock_info, mock_updater)
        assert is_running is True
        mock_updater.update_from_handle.assert_called_once_with(mock_info, mock_process_handle)

    def test_check_process_handle_no_processes_attribute(self, collector, mock_process_manager):
        """Test _check_process_handle when process_manager lacks 'processes' attribute."""
        del mock_process_manager.processes
        is_running = collector._check_process_handle("service_A", Mock(pid=123), Mock())
        assert is_running is False

    @pytest.mark.asyncio
    async def test_resolve_redis_pid_no_redis_processes(self, collector):
        """Test resolve_redis_pid returns None if no Redis processes found."""
        mock_process_monitor = Mock()
        mock_process_monitor.get_redis_processes = AsyncMock(return_value=[])

        pid = await collector.resolve_redis_pid(mock_process_monitor)
        assert pid is None
        mock_process_monitor.get_redis_processes.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resolve_redis_pid_with_redis_processes(self, collector):
        """Test resolve_redis_pid returns PID if Redis processes found."""
        mock_process_monitor = Mock()
        mock_process_monitor.get_redis_processes = AsyncMock(return_value=[Mock(pid=789)])

        pid = await collector.resolve_redis_pid(mock_process_monitor)
        assert pid == 789
        mock_process_monitor.get_redis_processes.assert_awaited_once()
