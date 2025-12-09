'"""Tests for the scraper connection manager."""'

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common import scraper_connection_manager as scraper_module

DEFAULT_SCRAPER_CONNECTION_LIMIT = 10
DEFAULT_SCRAPER_CONNECTION_LIMIT_PER_HOST = 5


def _build_manager():
    manager = scraper_module.ScraperConnectionManager.__new__(
        scraper_module.ScraperConnectionManager
    )
    manager.target_urls = ["https://kalshi.com"]
    manager.user_agent = "test-agent"

    manager.session_manager = MagicMock()
    manager.session_manager.is_session_valid.return_value = True

    session = MagicMock()
    session.closed = False
    connector = MagicMock()
    connector._limit = DEFAULT_SCRAPER_CONNECTION_LIMIT
    connector._limit_per_host = DEFAULT_SCRAPER_CONNECTION_LIMIT_PER_HOST
    connector._closed = False
    session._connector = connector
    manager.session_manager.get_session.return_value = session

    manager.health_monitor = MagicMock()
    manager.health_monitor.check_health = AsyncMock(return_value="healthy")
    manager.health_monitor.get_health_details.return_value = {"health": "ok"}

    manager.content_validator = MagicMock()
    manager.content_validator.get_validation_metrics.return_value = {"validations": 1}

    manager.lifecycle_manager = MagicMock()
    manager.lifecycle_manager.establish_connection = AsyncMock(return_value=True)
    manager.lifecycle_manager.cleanup_connection = AsyncMock()

    manager.scraping_ops = MagicMock()
    manager.scraping_ops.scrape_url = AsyncMock(return_value="body")
    manager.scraping_ops.scrape_all_urls = AsyncMock(return_value={"url": "body"})

    manager.get_status = MagicMock(return_value={"state": "ok"})

    return manager


@pytest.mark.asyncio
async def test_scraper_connection_manager_async_methods():
    manager = _build_manager()

    assert await manager.establish_connection()
    assert (
        await manager.check_connection_health() == manager.health_monitor.check_health.return_value
    )
    await manager.cleanup_connection()
    manager.lifecycle_manager.cleanup_connection.assert_awaited_once()
    assert await manager.scrape_url("https://kalshi.com") == "body"
    assert await manager.scrape_all_urls() == {"url": "body"}


def test_get_connection_info_includes_connector_details():
    manager = _build_manager()
    info = manager.get_connection_info()

    scraper_details = info["scraper_details"]
    assert scraper_details["target_urls"] == ["https://kalshi.com"]
    assert scraper_details["user_agent"] == "test-agent"
    assert scraper_details["session_closed"] is False
    assert scraper_details["connector_info"]["connection_limit"] == DEFAULT_SCRAPER_CONNECTION_LIMIT
