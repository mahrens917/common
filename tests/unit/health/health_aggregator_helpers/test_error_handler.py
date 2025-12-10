import unittest
from unittest.mock import MagicMock, Mock

from common.health.health_aggregator_helpers.error_handler import ErrorHandler
from common.health.log_activity_monitor import LogActivity, LogActivityStatus
from common.health.process_health_monitor import ProcessHealthInfo, ProcessStatus
from common.health.service_health_checker import ServiceHealth, ServiceHealthInfo


class TestErrorHandler(unittest.TestCase):
    def test_ensure_process_info_valid(self):
        valid_info = ProcessHealthInfo(status=ProcessStatus.RUNNING)
        result = ErrorHandler.ensure_process_info("service", valid_info)
        self.assertEqual(result, valid_info)

    def test_ensure_process_info_exception(self):
        exception = ValueError("Error")
        result = ErrorHandler.ensure_process_info("service", exception)
        self.assertIsInstance(result, ProcessHealthInfo)
        self.assertEqual(result.status, ProcessStatus.NOT_FOUND)

    def test_ensure_log_activity_valid(self):
        valid_info = LogActivity(status=LogActivityStatus.RECENT)
        result = ErrorHandler.ensure_log_activity("service", valid_info)
        self.assertEqual(result, valid_info)

    def test_ensure_log_activity_exception(self):
        exception = ValueError("Error")
        result = ErrorHandler.ensure_log_activity("service", exception)
        self.assertIsInstance(result, LogActivity)
        self.assertEqual(result.status, LogActivityStatus.ERROR)
        self.assertEqual(result.error_message, "Error")

    def test_ensure_service_health_valid(self):
        valid_info = ServiceHealthInfo(health=ServiceHealth.HEALTHY)
        result = ErrorHandler.ensure_service_health("service", valid_info)
        self.assertEqual(result, valid_info)

    def test_ensure_service_health_exception(self):
        exception = ValueError("Error")
        result = ErrorHandler.ensure_service_health("service", exception)
        self.assertIsInstance(result, ServiceHealthInfo)
        self.assertEqual(result.health, ServiceHealth.UNKNOWN)
        self.assertEqual(result.error_message, "Error")
