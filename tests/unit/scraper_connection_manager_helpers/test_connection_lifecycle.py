from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock

import aiohttp
import pytest

from src.common.scraper_connection_manager_helpers.connection_lifecycle import (
    ScraperConnectionLifecycle,
)


@pytest.mark.asyncio
async def test_establish_connection_success():
    session_manager = AsyncMock()
    session_manager.create_session = AsyncMock()
    health_monitor = Mock()
    health_monitor.check_health = AsyncMock(return_value=MagicMock(healthy=True))
    lifecycle = ScraperConnectionLifecycle("svc", session_manager, health_monitor)

    result = await lifecycle.establish_connection()

    assert result is True
    session_manager.create_session.assert_awaited_once()
    health_monitor.check_health.assert_awaited_once()


@pytest.mark.asyncio
async def test_establish_connection_fails_health_check_and_cleans_up():
    session_manager = AsyncMock()
    session_manager.create_session = AsyncMock()
    session_manager.close_session = AsyncMock()
    health_monitor = Mock()
    health_monitor.check_health = AsyncMock(return_value=MagicMock(healthy=False))
    health_monitor.clear_health_status = Mock()
    lifecycle = ScraperConnectionLifecycle("svc", session_manager, health_monitor)

    with pytest.raises(ConnectionError):
        await lifecycle.establish_connection()

    session_manager.create_session.assert_awaited_once()
    session_manager.close_session.assert_awaited_once()
    health_monitor.clear_health_status.assert_called_once()


@pytest.mark.asyncio
async def test_establish_connection_handles_timeout():
    session_manager = AsyncMock()
    session_manager.create_session = AsyncMock(side_effect=asyncio.TimeoutError())
    session_manager.close_session = AsyncMock()
    health_monitor = Mock()
    health_monitor.clear_health_status = Mock()
    lifecycle = ScraperConnectionLifecycle("svc", session_manager, health_monitor)

    with pytest.raises(TimeoutError):
        await lifecycle.establish_connection()

    session_manager.close_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_establish_connection_handles_client_error():
    session_manager = AsyncMock()
    session_manager.create_session = AsyncMock(side_effect=aiohttp.ClientError("boom"))
    session_manager.close_session = AsyncMock()
    health_monitor = Mock()
    health_monitor.clear_health_status = Mock()
    lifecycle = ScraperConnectionLifecycle("svc", session_manager, health_monitor)

    with pytest.raises(ConnectionError):
        await lifecycle.establish_connection()

    session_manager.close_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_connection_calls_close_and_clear():
    session_manager = AsyncMock()
    session_manager.close_session = AsyncMock()
    health_monitor = Mock()
    health_monitor.clear_health_status = Mock()
    lifecycle = ScraperConnectionLifecycle("svc", session_manager, health_monitor)

    await lifecycle.cleanup_connection()

    session_manager.close_session.assert_awaited_once()
    health_monitor.clear_health_status.assert_called_once()
