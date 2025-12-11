"""Unit tests for log_activity_collector."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from redis.exceptions import RedisError

from common.health.log_activity_monitor import LogActivity, LogActivityStatus
from common.optimized_status_reporter_helpers.log_activity_collector import (
    LogActivityCollector,
)
from common.redis_utils import RedisOperationError


class TestLogActivityCollector:
    """Tests for LogActivityCollector."""

    @pytest.fixture
    def mock_process_manager(self):
        """Mock process manager with services."""
        pm = Mock()
        # Use MagicMock for services so its keys() method can be directly mocked
        pm.services = MagicMock()
        pm.services.keys.return_value = ["service_A", "service_B"]
        return pm

    @pytest.fixture
    def collector(self, mock_process_manager):
        """LogActivityCollector instance with mocked dependencies."""
        # Patch LogActivityMonitor during initialization
        with patch("common.optimized_status_reporter_helpers.log_activity_collector.LogActivityMonitor") as mock_monitor_class:
            mock_monitor_class.return_value = AsyncMock()  # Make the instance an AsyncMock
            mock_monitor_instance = mock_monitor_class.return_value
            mock_monitor_instance.get_all_service_log_activity.return_value = {}  # Default mock return value
            instance = LogActivityCollector(mock_process_manager)
            instance._log_activity_monitor = mock_monitor_instance  # Store the mock instance
            return instance

    def test_init_sets_up_monitor(self, mock_process_manager):
        """Test initialization correctly sets up LogActivityMonitor."""
        with patch("common.optimized_status_reporter_helpers.log_activity_collector.LogActivityMonitor") as mock_monitor_class:
            with patch.object(
                Path,
                "resolve",
                return_value=Path("/root/project/src/common/optimized_status_reporter_helpers/log_activity_collector.py"),
            ) as mock_resolve:
                collector = LogActivityCollector(mock_process_manager)
                mock_monitor_class.assert_called_once_with(str(Path("/root/project/logs")))

    @pytest.mark.asyncio
    async def test_collect_log_activity_map_success_all_fresh(self, collector, mock_process_manager):
        """Test successful collection with all logs fresh."""
        collector._log_activity_monitor.get_all_service_log_activity.return_value = {
            "service_A": LogActivity(
                status=LogActivityStatus.RECENT,
                last_timestamp=Mock(),
                age_seconds=10.0,
                log_file_path="path_A",
            ),
            "service_B": LogActivity(
                status=LogActivityStatus.RECENT,
                last_timestamp=Mock(),
                age_seconds=10.0,
                log_file_path="path_B",
            ),
            "monitor": LogActivity(
                status=LogActivityStatus.RECENT,
                last_timestamp=Mock(),
                age_seconds=10.0,
                log_file_path="path_M",
            ),
        }
        mock_process_manager.services.keys.return_value = ["service_A", "service_B"]

        log_activity, stale_logs = await collector.collect_log_activity_map()

        assert len(log_activity) == 3
        assert not stale_logs
        collector._log_activity_monitor.get_all_service_log_activity.assert_awaited_once_with(["monitor", "service_A", "service_B"])

    @pytest.mark.asyncio
    async def test_collect_log_activity_map_success_some_stale(self, collector, mock_process_manager):
        """Test successful collection with some logs stale."""
        collector._log_activity_monitor.get_all_service_log_activity.return_value = {
            "service_A": LogActivity(
                status=LogActivityStatus.RECENT,
                last_timestamp=Mock(),
                age_seconds=10.0,
                log_file_path="path_A",
            ),
            "service_B": LogActivity(
                status=LogActivityStatus.STALE,
                last_timestamp=Mock(),
                age_seconds=100.0,
                log_file_path="path_B",
            ),
            "monitor": LogActivity(
                status=LogActivityStatus.OLD,
                last_timestamp=Mock(),
                age_seconds=1000.0,
                log_file_path="path_M",
            ),
        }
        mock_process_manager.services.keys.return_value = ["service_A", "service_B"]

        log_activity, stale_logs = await collector.collect_log_activity_map()
        print(f"log_activity in test_collect_log_activity_map_success_some_stale: {log_activity}")
        assert len(log_activity) == 3
        assert sorted(stale_logs) == ["monitor", "service_B"]

    @pytest.mark.asyncio
    async def test_collect_log_activity_map_no_services(self, collector, mock_process_manager):
        """Test collection when no services are configured."""
        mock_process_manager.services = {}
        collector._log_activity_monitor.get_all_service_log_activity.return_value = {
            "monitor": LogActivity(
                status=LogActivityStatus.RECENT,
                last_timestamp=Mock(),
                age_seconds=10.0,
                log_file_path="path_M",
            )
        }

        log_activity, stale_logs = await collector.collect_log_activity_map()

        assert len(log_activity) == 1
        assert not stale_logs
        collector._log_activity_monitor.get_all_service_log_activity.assert_awaited_once_with(["monitor"])

    @pytest.mark.asyncio
    async def test_collect_log_activity_map_exception_handling(self, collector):
        """Test exception handling during log activity gathering."""
        # Use RedisError as an example of LOG_ACTIVITY_ERRORS
        collector._log_activity_monitor.get_all_service_log_activity.side_effect = RedisError("Test error")

        log_activity, stale_logs = await collector.collect_log_activity_map()

        assert not log_activity
        assert not stale_logs
        collector._log_activity_monitor.get_all_service_log_activity.assert_awaited_once()
