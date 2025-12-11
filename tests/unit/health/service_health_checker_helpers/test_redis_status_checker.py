import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from common.health.service_health_checker_helpers.redis_status_checker import check_redis_status
from common.health.service_health_types import ServiceHealth, ServiceHealthInfo


class TestRedisStatusChecker(unittest.IsolatedAsyncioTestCase):
    async def test_check_redis_status_success(self):
        redis_client = Mock()
        redis_client.hgetall = AsyncMock(return_value={b"status": b"healthy", b"timestamp": b"1234567890.0"})

        # We need to mock evaluate_status_health since it contains logic we want to bypass or test integrally
        # Here I'll just let it run if it's simple, but better to mock it if we only test redis fetching logic
        with patch("common.health.service_health_checker_helpers.redis_status_checker.evaluate_status_health") as mock_eval:
            mock_eval.return_value = ServiceHealthInfo(health=ServiceHealth.HEALTHY)

            result = await check_redis_status("service", redis_client)
            self.assertEqual(result.health, ServiceHealth.HEALTHY)
            mock_eval.assert_called()

    async def test_check_redis_status_no_data(self):
        redis_client = Mock()
        redis_client.hgetall = AsyncMock(return_value={})

        result = await check_redis_status("service", redis_client)
        self.assertEqual(result.health, ServiceHealth.UNRESPONSIVE)
        self.assertIn("No status data", result.error_message)

    async def test_check_redis_status_missing_timestamp(self):
        redis_client = Mock()
        redis_client.hgetall = AsyncMock(return_value={b"status": b"healthy"})

        result = await check_redis_status("service", redis_client)
        self.assertEqual(result.health, ServiceHealth.UNRESPONSIVE)
        self.assertIn("No timestamp", result.error_message)

    async def test_check_redis_status_empty_timestamp(self):
        redis_client = Mock()
        redis_client.hgetall = AsyncMock(return_value={b"status": b"healthy", b"timestamp": b""})

        result = await check_redis_status("service", redis_client)
        self.assertEqual(result.health, ServiceHealth.UNRESPONSIVE)
        self.assertIn("No timestamp", result.error_message)

    async def test_check_redis_status_invalid_timestamp(self):
        redis_client = Mock()
        redis_client.hgetall = AsyncMock(return_value={b"status": b"healthy", b"timestamp": b"invalid"})

        result = await check_redis_status("service", redis_client)
        self.assertEqual(result.health, ServiceHealth.UNRESPONSIVE)
        self.assertIn("Invalid timestamp", result.error_message)

    async def test_check_redis_status_redis_error(self):
        redis_client = Mock()
        redis_client.hgetall = AsyncMock(side_effect=ConnectionError("Redis down"))

        result = await check_redis_status("service", redis_client)
        self.assertEqual(result.health, ServiceHealth.UNKNOWN)
        self.assertIn("Redis check failed", result.error_message)
