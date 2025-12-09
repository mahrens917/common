import pytest

from src.common.simple_health_checker_helpers.types import HealthStatus, ServiceHealth


class TestTypes:
    def test_health_status_enum(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_service_health_dataclass(self):
        health = ServiceHealth(
            service_name="test_service",
            status=HealthStatus.HEALTHY,
            response_time_ms=100.0,
            last_log_update=1234567890.0,
            error_message=None,
            activity_status="Active",
            seconds_since_last_log=10,
        )

        assert health.service_name == "test_service"
        assert health.status == HealthStatus.HEALTHY
        assert health.response_time_ms == 100.0
        assert health.last_log_update == 1234567890.0
        assert health.error_message is None
        assert health.activity_status == "Active"
        assert health.seconds_since_last_log == 10

    def test_service_health_defaults(self):
        health = ServiceHealth(service_name="test", status=HealthStatus.UNKNOWN)
        assert health.response_time_ms is None
        assert health.last_log_update is None
        assert health.error_message is None
        assert health.activity_status is None
        assert health.seconds_since_last_log is None
