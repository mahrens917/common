import time
from unittest.mock import Mock, patch

import pytest

from src.common.simple_health_checker_helpers.log_health_checker import LogHealthChecker
from src.common.simple_health_checker_helpers.types import HealthStatus


class TestLogHealthChecker:
    def test_check_log_health_success(self):
        classifier = Mock()
        classifier.classify_log_activity.return_value = "Active"
        checker = LogHealthChecker("/logs", 100, classifier)

        with (
            patch("os.path.join", return_value="/logs/test.log"),
            patch("os.path.exists", return_value=True),
            patch("os.path.getmtime", return_value=time.time() - 10),
        ):

            # We don't need to mock time.time() because we calc age relative to it
            # But getmtime returns timestamp.
            # age = time.time() - (time.time() - 10) = 10.

            result = asyncio_run(checker.check_log_health("test"))

            assert result.status == HealthStatus.HEALTHY
            assert result.seconds_since_last_log == 10
            assert result.activity_status == "Active"

    def test_check_log_health_stale(self):
        classifier = Mock()
        classifier.classify_log_activity.return_value = "Stale"
        checker = LogHealthChecker("/logs", 5, classifier)  # 5s threshold

        with (
            patch("os.path.join", return_value="/logs/test.log"),
            patch("os.path.exists", return_value=True),
            patch("os.path.getmtime", return_value=time.time() - 10),
        ):  # 10s old

            result = asyncio_run(checker.check_log_health("test"))

            assert result.status == HealthStatus.UNHEALTHY
            assert "Log stale" in result.error_message
            assert result.seconds_since_last_log == 10

    def test_check_log_health_missing_file(self):
        classifier = Mock()
        checker = LogHealthChecker("/logs", 100, classifier)

        with (
            patch("os.path.join", return_value="/logs/test.log"),
            patch("os.path.exists", return_value=False),
        ):

            result = asyncio_run(checker.check_log_health("test"))

            assert result.status == HealthStatus.UNHEALTHY
            assert result.error_message == "Log file not found"

    def test_check_log_health_os_error(self):
        classifier = Mock()
        checker = LogHealthChecker("/logs", 100, classifier)

        with (
            patch("os.path.join", return_value="/logs/test.log"),
            patch("os.path.exists", return_value=True),
            patch("os.path.getmtime", side_effect=OSError("Disk error")),
        ):

            result = asyncio_run(checker.check_log_health("test"))

            assert result.status == HealthStatus.UNKNOWN
            assert "Log check error" in result.error_message


# Helper to run async
import asyncio


def asyncio_run(coro):
    return asyncio.run(coro)
