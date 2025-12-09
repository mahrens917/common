import unittest
from unittest.mock import Mock

from src.common.health.health_aggregator_helpers.status_builder import StatusBuilder
from src.common.health.health_types import OverallServiceStatus
from src.common.health.log_activity_monitor import LogActivity
from src.common.health.process_health_monitor import ProcessHealthInfo, ProcessStatus
from src.common.health.service_health_checker import ServiceHealth, ServiceHealthInfo


class TestStatusBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = StatusBuilder()
        # Mock formatter to simplify assertions
        self.builder.formatter = Mock()
        self.builder.formatter.format_log_age.return_value = "LOG_MSG"

    def test_build_unresponsive_status(self):
        log_activity = Mock(spec=LogActivity)
        result = self.builder.build_unresponsive_status(log_activity)
        self.assertEqual(result[0], OverallServiceStatus.UNRESPONSIVE)
        self.assertEqual(result[1], "🔴")
        self.assertEqual(result[2], "Unresponsive")
        self.assertIn("health: unresponsive", result[3])

    def test_build_silent_status_from_logs(self):
        log_activity = Mock(spec=LogActivity)

        # With HEALTHY
        service_health = Mock(spec=ServiceHealthInfo)
        service_health.health = ServiceHealth.HEALTHY
        result = self.builder.build_silent_status_from_logs(log_activity, service_health)
        self.assertEqual(result[0], OverallServiceStatus.SILENT)
        self.assertIn("health: responding", result[3])

        # With UNRESPONSIVE
        service_health.health = ServiceHealth.UNRESPONSIVE
        # Mock the value property if needed, or assume Enum member
        result = self.builder.build_silent_status_from_logs(log_activity, service_health)
        self.assertEqual(result[0], OverallServiceStatus.SILENT)
        # "unresponsive" string comes from enum value

    def test_build_degraded_status(self):
        log_activity = Mock(spec=LogActivity)
        result = self.builder.build_degraded_status(log_activity)
        self.assertEqual(result[0], OverallServiceStatus.DEGRADED)
        self.assertIn("health: degraded", result[3])

    def test_build_silent_status_from_stale_logs(self):
        log_activity = Mock(spec=LogActivity)
        result = self.builder.build_silent_status_from_stale_logs(log_activity)
        self.assertEqual(result[0], OverallServiceStatus.SILENT)
        self.assertIn("health: responding", result[3])

    def test_build_healthy_status(self):
        log_activity = Mock(spec=LogActivity)
        result = self.builder.build_healthy_status(log_activity)
        self.assertEqual(result[0], OverallServiceStatus.HEALTHY)
        self.assertEqual(result[1], "🟢")
        self.assertIn("health: responding", result[3])

    def test_build_error_status(self):
        process_info = Mock(spec=ProcessHealthInfo)
        process_info.status = ProcessStatus.STOPPED
        log_activity = Mock(spec=LogActivity)
        service_health = Mock(spec=ServiceHealthInfo)
        service_health.health = ServiceHealth.UNRESPONSIVE

        result = self.builder.build_error_status(process_info, log_activity, service_health)
        self.assertEqual(result[0], OverallServiceStatus.ERROR)
        self.assertEqual(result[1], "🔴")
        self.assertIn("process: stopped", result[3])
