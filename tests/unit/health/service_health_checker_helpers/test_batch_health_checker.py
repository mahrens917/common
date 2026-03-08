"""Tests for batch_health_checker module."""

import time
import unittest
from unittest.mock import AsyncMock, patch

from common.health.service_health_checker_helpers.batch_health_checker import (
    check_all_service_health,
    evaluate_status_health,
)
from common.health.service_health_types import ServiceHealth, ServiceHealthInfo


class TestCheckAllServiceHealth(unittest.IsolatedAsyncioTestCase):
    async def test_returns_results_for_all_services(self):
        async def mock_check(name):
            return ServiceHealthInfo(health=ServiceHealth.HEALTHY)

        result = await check_all_service_health(["svc1", "svc2"], mock_check)
        self.assertEqual(len(result), 2)
        self.assertEqual(result["svc1"].health, ServiceHealth.HEALTHY)
        self.assertEqual(result["svc2"].health, ServiceHealth.HEALTHY)

    async def test_handles_exception_from_service_check(self):
        async def mock_check(name):
            raise RuntimeError("check failed")

        result = await check_all_service_health(["svc1"], mock_check)
        self.assertEqual(result["svc1"].health, ServiceHealth.UNKNOWN)
        self.assertIn("check failed", result["svc1"].error_message)

    async def test_empty_service_list(self):
        async def mock_check(name):
            return ServiceHealthInfo(health=ServiceHealth.HEALTHY)

        result = await check_all_service_health([], mock_check)
        self.assertEqual(result, {})


class TestEvaluateStatusHealth(unittest.TestCase):
    def test_failed_service_returns_unresponsive(self):
        with (
            patch("common.service_status.is_service_failed", return_value=True),
            patch("common.service_status.is_service_ready", return_value=False),
        ):
            result = evaluate_status_health("failed", 1000.0)
        self.assertEqual(result.health, ServiceHealth.UNRESPONSIVE)
        self.assertIn("failed", result.error_message)

    def test_ready_service_recent_returns_healthy(self):
        now = time.time()
        with (
            patch("common.service_status.is_service_failed", return_value=False),
            patch("common.service_status.is_service_ready", return_value=True),
        ):
            result = evaluate_status_health("ready", now - 10)
        self.assertEqual(result.health, ServiceHealth.HEALTHY)

    def test_ready_service_stale_returns_degraded(self):
        with (
            patch("common.service_status.is_service_failed", return_value=False),
            patch("common.service_status.is_service_ready", return_value=True),
        ):
            result = evaluate_status_health("ready", 0.0)
        self.assertEqual(result.health, ServiceHealth.DEGRADED)
        self.assertIn("stale", result.error_message)

    def test_unknown_status_returns_degraded(self):
        with (
            patch("common.service_status.is_service_failed", return_value=False),
            patch("common.service_status.is_service_ready", return_value=False),
        ):
            result = evaluate_status_health("unknown_status", 1000.0)
        self.assertEqual(result.health, ServiceHealth.DEGRADED)
        self.assertIn("Unknown status", result.error_message)
