import asyncio
import logging
import unittest
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from common.scraper_connection_manager_helpers.health_monitor_helpers.health_checker import (
    HealthChecker,
)
from common.scraper_connection_manager_helpers.health_monitor_helpers.url_checker import (
    check_url_health,
)
from common.scraper_connection_manager_helpers.health_monitor_helpers.url_tester import (
    URLTester,
)


class TestHealthCheckerHelper(unittest.TestCase):
    def test_calculate_threshold(self):
        assert HealthChecker.calculate_threshold(1) == 1
        assert HealthChecker.calculate_threshold(2) == 1
        assert HealthChecker.calculate_threshold(3) == 1
        assert HealthChecker.calculate_threshold(4) == 2
        assert HealthChecker.calculate_threshold(5) == 2

    def test_evaluate_health(self):
        assert HealthChecker.evaluate_health(1, 1) is True
        assert HealthChecker.evaluate_health(0, 1) is False
        assert HealthChecker.evaluate_health(1, 2) is True
        assert HealthChecker.evaluate_health(1, 3) is True
        assert HealthChecker.evaluate_health(2, 4) is True
        assert HealthChecker.evaluate_health(1, 4) is False

    def test_update_success_metrics(self):
        health_status = {}
        loop = Mock()
        loop.time.return_value = 100.0
        logger = Mock()

        HealthChecker.update_success_metrics(health_status, loop, 2, 2, logger)

        assert health_status["last_successful_scrape_time"] == 100.0
        assert health_status["consecutive_scrape_failures"] == 0
        logger.debug.assert_called()

    def test_update_failure_metrics(self):
        health_status = {"consecutive_scrape_failures": 1}
        logger = Mock()

        HealthChecker.update_failure_metrics(health_status, 0, 2, 1, logger)

        assert health_status["consecutive_scrape_failures"] == 2
        logger.warning.assert_called()


class TestUrlChecker(unittest.IsolatedAsyncioTestCase):
    async def test_check_url_health_success(self):
        mock_session = Mock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_response

        mock_validator = Mock()
        mock_validator.has_validators.return_value = False

        logger = Mock()

        result = await check_url_health("http://test.url", mock_session, mock_validator, logger)
        assert result is True

    async def test_check_url_health_bad_status(self):
        mock_session = Mock()
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_response

        mock_validator = Mock()
        logger = Mock()

        result = await check_url_health("http://test.url", mock_session, mock_validator, logger)
        assert result is False
        logger.warning.assert_called()

    async def test_check_url_health_validation_failure(self):
        mock_session = Mock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "bad"
        mock_response.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_response

        mock_validator = Mock()
        mock_validator.has_validators.return_value = True
        mock_validator.validate_content = AsyncMock(return_value=False)

        logger = Mock()

        result = await check_url_health("http://test.url", mock_session, mock_validator, logger)
        assert result is False
        logger.warning.assert_called()

    async def test_check_url_health_timeout(self):
        mock_session = Mock()
        mock_session.get.side_effect = asyncio.TimeoutError()

        mock_validator = Mock()
        logger = Mock()

        result = await check_url_health("http://test.url", mock_session, mock_validator, logger)
        assert result is False
        logger.warning.assert_called()

    async def test_check_url_health_client_error(self):
        mock_session = Mock()
        mock_session.get.side_effect = aiohttp.ClientError("error")

        mock_validator = Mock()
        logger = Mock()

        result = await check_url_health("http://test.url", mock_session, mock_validator, logger)
        assert result is False
        logger.warning.assert_called()

    async def test_check_url_health_unexpected_error(self):
        mock_session = Mock()
        mock_session.get.side_effect = ValueError("error")

        mock_validator = Mock()
        logger = Mock()

        result = await check_url_health("http://test.url", mock_session, mock_validator, logger)
        assert result is False
        logger.exception.assert_called()


class TestUrlTester(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.logger = Mock()
        self.tester = URLTester(self.logger)

    async def test_test_url_success(self):
        mock_session = Mock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_response

        mock_validator = Mock()
        mock_validator.has_validators.return_value = False

        result = await self.tester.test_url("http://test.url", mock_session, mock_validator)
        assert result is True

    async def test_test_url_bad_status(self):
        mock_session = Mock()
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_response

        mock_validator = Mock()

        result = await self.tester.test_url("http://test.url", mock_session, mock_validator)
        assert result is False
        self.logger.warning.assert_called()

    async def test_test_url_validation_failure(self):
        mock_session = Mock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "bad"
        mock_response.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_response

        mock_validator = Mock()
        mock_validator.has_validators.return_value = True
        mock_validator.validate_content = AsyncMock(return_value=False)

        result = await self.tester.test_url("http://test.url", mock_session, mock_validator)
        assert result is False
        self.logger.warning.assert_called()

    async def test_test_url_timeout(self):
        mock_session = Mock()
        mock_session.get.side_effect = asyncio.TimeoutError()

        mock_validator = Mock()

        result = await self.tester.test_url("http://test.url", mock_session, mock_validator)
        assert result is False
        self.logger.warning.assert_called()

    async def test_test_url_client_error(self):
        mock_session = Mock()
        mock_session.get.side_effect = aiohttp.ClientError("error")

        mock_validator = Mock()

        result = await self.tester.test_url("http://test.url", mock_session, mock_validator)
        assert result is False
        self.logger.warning.assert_called()

    async def test_test_url_unexpected_error(self):
        mock_session = Mock()
        mock_session.get.side_effect = ValueError("error")

        mock_validator = Mock()

        result = await self.tester.test_url("http://test.url", mock_session, mock_validator)
        assert result is False
        self.logger.exception.assert_called()
