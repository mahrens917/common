from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.common.simple_health_checker_helpers.simple_health_delegator import SimpleHealthDelegator
from src.common.simple_health_checker_helpers.types import HealthStatus, ServiceHealth


class TestSimpleHealthDelegator:
    def test_init(self):
        delegator = SimpleHealthDelegator(
            logs_directory="/logs",
            health_timeout_seconds=5,
            log_staleness_threshold_seconds=60,
            active_threshold_seconds=300,
            fresh_threshold_seconds=3600,
        )
        assert delegator.health_url_provider is not None
        assert delegator.http_health_checker is not None
        assert delegator.log_health_checker is not None
        assert delegator.multi_service_checker is not None

    @pytest.mark.asyncio
    async def test_check_service_health_healthy(self):
        delegator = SimpleHealthDelegator("/logs", 5, 60, 300, 3600)
        delegator.health_url_provider.get_health_urls = Mock(return_value=["url"])

        delegator.http_health_checker.check_http_health = AsyncMock(
            return_value=ServiceHealth("test", HealthStatus.HEALTHY)
        )

        result = await delegator.check_service_health("test")
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_service_health_unhealthy(self):
        delegator = SimpleHealthDelegator("/logs", 5, 60, 300, 3600)
        delegator.health_url_provider.get_health_urls = Mock(return_value=["url"])

        delegator.http_health_checker.check_http_health = AsyncMock(
            return_value=ServiceHealth("test", HealthStatus.UNHEALTHY)
        )

        result = await delegator.check_service_health("test")
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_multiple_services(self):
        delegator = SimpleHealthDelegator("/logs", 5, 60, 300, 3600)
        delegator.multi_service_checker.check_multiple_services = AsyncMock(return_value={})

        await delegator.check_multiple_services(["s1"])
        delegator.multi_service_checker.check_multiple_services.assert_called_once_with(["s1"])

    def test_is_service_healthy(self):
        delegator = SimpleHealthDelegator("/logs", 5, 60, 300, 3600)
        assert delegator.is_service_healthy(ServiceHealth("t", HealthStatus.HEALTHY)) is True
        assert delegator.is_service_healthy(ServiceHealth("t", HealthStatus.UNHEALTHY)) is False

    @pytest.mark.asyncio
    async def test_get_detailed_service_status_success(self):
        delegator = SimpleHealthDelegator("/logs", 5, 60, 300, 3600)
        delegator.log_health_checker.check_log_health = AsyncMock(
            return_value=ServiceHealth("test", HealthStatus.HEALTHY)
        )

        result = await delegator.get_detailed_service_status("test")
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_get_detailed_service_status_failure(self):
        delegator = SimpleHealthDelegator("/logs", 5, 60, 300, 3600)
        delegator.log_health_checker.check_log_health = AsyncMock(
            return_value=ServiceHealth("test", HealthStatus.UNKNOWN)
        )

        with pytest.raises(RuntimeError):
            await delegator.get_detailed_service_status("test")
