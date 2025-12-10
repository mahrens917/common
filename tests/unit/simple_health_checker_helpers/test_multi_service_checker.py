from unittest.mock import AsyncMock

import pytest

from common.simple_health_checker_helpers.multi_service_checker import MultiServiceChecker
from common.simple_health_checker_helpers.types import HealthStatus, ServiceHealth


class TestMultiServiceChecker:
    @pytest.mark.asyncio
    async def test_check_multiple_services_success(self):
        async def mock_check(name):
            return ServiceHealth(name, HealthStatus.HEALTHY)

        checker = MultiServiceChecker(mock_check)
        results = await checker.check_multiple_services(["s1", "s2"])

        assert len(results) == 2
        assert results["s1"].status == HealthStatus.HEALTHY
        assert results["s2"].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_multiple_services_with_exception(self):
        async def mock_check(name):
            if name == "fail":
                raise ValueError("Failed")
            return ServiceHealth(name, HealthStatus.HEALTHY)

        checker = MultiServiceChecker(mock_check)
        results = await checker.check_multiple_services(["ok", "fail"])

        assert len(results) == 2
        assert results["ok"].status == HealthStatus.HEALTHY
        assert results["fail"].status == HealthStatus.UNKNOWN
        assert "Failed" in results["fail"].error_message
