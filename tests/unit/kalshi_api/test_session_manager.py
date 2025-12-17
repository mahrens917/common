"""Tests for kalshi_api session_manager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.kalshi_api.client import KalshiConfig
from common.kalshi_api.session_manager import SessionManager


@pytest.fixture
def config():
    return KalshiConfig()


@pytest.fixture
def session_manager(config):
    return SessionManager(config)


def test_init(session_manager, config):
    assert session_manager._config is config
    assert session_manager._session is None
    assert isinstance(session_manager._session_lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_initialize_creates_session(session_manager):
    with patch("common.kalshi_api.session_manager.aiohttp.ClientSession") as mock_session:
        mock_session.return_value = MagicMock()
        mock_session.return_value.closed = False

        await session_manager.initialize()

        mock_session.assert_called_once()
        assert session_manager._session is not None


@pytest.mark.asyncio
async def test_initialize_skips_if_session_exists(session_manager):
    mock_session = MagicMock()
    mock_session.closed = False
    session_manager._session = mock_session

    with patch("common.kalshi_api.session_manager.aiohttp.ClientSession") as new_session:
        await session_manager.initialize()

        new_session.assert_not_called()


@pytest.mark.asyncio
async def test_close_closes_session(session_manager):
    mock_session = AsyncMock()
    session_manager._session = mock_session

    await session_manager.close()

    mock_session.close.assert_called_once()
    assert session_manager._session is None


@pytest.mark.asyncio
async def test_close_no_session(session_manager):
    await session_manager.close()  # Should not raise


def test_get_session_raises_if_not_initialized(session_manager):
    with pytest.raises(RuntimeError) as exc_info:
        session_manager.get_session()

    assert "not initialized" in str(exc_info.value)


def test_get_session_returns_session(session_manager):
    mock_session = MagicMock()
    session_manager._session = mock_session

    result = session_manager.get_session()

    assert result is mock_session


def test_session_property(session_manager):
    assert session_manager.session is None

    mock_session = MagicMock()
    session_manager._session = mock_session

    assert session_manager.session is mock_session


def test_set_session(session_manager):
    mock_session = MagicMock()

    session_manager.set_session(mock_session)

    assert session_manager._session is mock_session


def test_session_lock_property(session_manager):
    assert isinstance(session_manager.session_lock, asyncio.Lock)


def test_set_session_lock(session_manager):
    new_lock = asyncio.Lock()

    session_manager.set_session_lock(new_lock)

    assert session_manager._session_lock is new_lock
