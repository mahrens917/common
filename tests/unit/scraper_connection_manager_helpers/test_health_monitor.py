import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest

from src.common.health.types import HealthCheckResult
from src.common.scraper_connection_manager_helpers.health_monitor import ScraperHealthMonitor


class TestScraperHealthMonitor:
    @pytest.fixture
    def session_provider(self):
        provider = Mock()
        session = MagicMock(spec=aiohttp.ClientSession)
        session.closed = False
        # Ensure get is a MagicMock, not AsyncMock, because it returns a context manager
        session.get = MagicMock()
        provider.get_session.return_value = session
        return provider

    @pytest.fixture
    def content_validator(self):
        validator = Mock()
        validator.has_validators.return_value = False
        validator.validate_content = AsyncMock(return_value=True)
        return validator

    @pytest.fixture
    def monitor(self, session_provider, content_validator):
        return ScraperHealthMonitor(
            service_name="test_service",
            target_urls=["http://test.url/1", "http://test.url/2"],
            session_provider=session_provider,
            content_validator=content_validator,
        )

    @pytest.mark.asyncio
    async def test_check_health_success(self, monitor, session_provider):
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "ok"

        # Mock context manager
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None

        session = session_provider.get_session.return_value
        session.get.return_value = mock_cm

        result = await monitor.check_health()

        assert result.healthy is True
        assert len(monitor.url_health_status) == 2
        assert all(monitor.url_health_status.values())
        assert monitor.last_success_time > 0
        assert monitor.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_check_health_session_closed(self, monitor, session_provider):
        session = session_provider.get_session.return_value
        session.closed = True

        result = await monitor.check_health()

        assert result.healthy is False
        assert result.error == "session_closed"
        assert monitor.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_check_health_partial_failure(self, monitor, session_provider):
        # One success, one failure

        def side_effect(url, timeout):
            mock_response = AsyncMock()
            if url == "http://test.url/1":
                mock_response.status = 200
            else:
                mock_response.status = 500

            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_response
            mock_cm.__aexit__.return_value = None
            return mock_cm

        session = session_provider.get_session.return_value
        session.get.side_effect = side_effect

        result = await monitor.check_health()

        # 1/2 healthy -> 50% -> success (threshold is max(1, 2//2) = 1)
        assert result.healthy is True
        assert monitor.url_health_status["http://test.url/1"] is True
        assert monitor.url_health_status["http://test.url/2"] is False

    @pytest.mark.asyncio
    async def test_check_health_total_failure(self, monitor, session_provider):
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None

        session = session_provider.get_session.return_value
        session.get.return_value = mock_cm

        result = await monitor.check_health()

        assert result.healthy is False
        assert result.error == "insufficient_healthy_urls"
        assert all(not status for status in monitor.url_health_status.values())

    @pytest.mark.asyncio
    async def test_check_health_timeout(self, monitor, session_provider):
        session = session_provider.get_session.return_value
        # Context manager enters then raises TimeoutError
        mock_cm = MagicMock()
        mock_cm.__aenter__.side_effect = asyncio.TimeoutError()
        session.get.return_value = mock_cm

        result = await monitor.check_health()

        assert result.healthy is False
        assert all(not status for status in monitor.url_health_status.values())

    @pytest.mark.asyncio
    async def test_check_health_client_error(self, monitor, session_provider):
        session = session_provider.get_session.return_value
        mock_cm = MagicMock()
        mock_cm.__aenter__.side_effect = aiohttp.ClientError("connection error")
        session.get.return_value = mock_cm

        result = await monitor.check_health()

        assert result.healthy is False

    @pytest.mark.asyncio
    async def test_check_health_content_validation_failure(
        self, monitor, session_provider, content_validator
    ):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "invalid content"

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None

        session = session_provider.get_session.return_value
        session.get.return_value = mock_cm

        content_validator.has_validators.return_value = True
        content_validator.validate_content.return_value = False

        result = await monitor.check_health()

        assert result.healthy is False
        assert all(not status for status in monitor.url_health_status.values())

    @pytest.mark.asyncio
    async def test_check_health_unexpected_error(self, monitor, session_provider):
        session = session_provider.get_session.return_value
        mock_cm = MagicMock()
        mock_cm.__aenter__.side_effect = ValueError("unexpected")
        session.get.return_value = mock_cm

        result = await monitor.check_health()

        assert result.healthy is False

    def test_clear_health_status(self, monitor):
        monitor.url_health_status = {"url1": True}
        monitor.clear_health_status()
        assert monitor.url_health_status == {}

    def test_get_health_details(self, monitor):
        monitor.url_health_status = {"url1": True}
        monitor.last_success_time = 12345.0
        monitor.consecutive_failures = 2

        details = monitor.get_health_details()

        assert details["url_health_status"] == {"url1": True}
        assert details["last_successful_scrape_time"] == 12345.0
        assert details["consecutive_scrape_failures"] == 2
