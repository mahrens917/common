"""Tests for reconnection manager module."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.base_connection_manager_helpers.health_coordinator_helpers.reconnection_manager import (
    ReconnectionManager,
)


class TestReconnectionManagerInit:
    """Tests for ReconnectionManager initialization."""

    def test_init_stores_dependencies(self) -> None:
        """Initialization stores all dependencies."""
        mock_logger = MagicMock()

        manager = ReconnectionManager("test_service", mock_logger)

        assert manager.service_name == "test_service"
        assert manager.logger is mock_logger


class TestReconnectionManagerHandleDisconnected:
    """Tests for ReconnectionManager.handle_disconnected."""

    @pytest.mark.asyncio
    async def test_returns_true_and_starts_task(self) -> None:
        """Returns True and starts reconnection task when no task running."""
        mock_logger = MagicMock()
        manager = ReconnectionManager("test_service", mock_logger)

        mock_connect = AsyncMock()
        mock_task = None

        result, new_task = await manager.handle_disconnected(mock_connect, mock_task)

        assert result is True
        assert new_task is not None

    @pytest.mark.asyncio
    async def test_returns_existing_task_when_running(self) -> None:
        """Returns existing task when it's still running."""
        mock_logger = MagicMock()
        manager = ReconnectionManager("test_service", mock_logger)

        mock_connect = AsyncMock()
        mock_task = MagicMock()
        mock_task.done.return_value = False

        result, new_task = await manager.handle_disconnected(mock_connect, mock_task)

        assert result is True
        assert new_task is mock_task

    @pytest.mark.asyncio
    async def test_starts_new_task_when_previous_done(self) -> None:
        """Starts new task when previous task is done."""
        mock_logger = MagicMock()
        manager = ReconnectionManager("test_service", mock_logger)

        mock_connect = AsyncMock()
        mock_task = MagicMock()
        mock_task.done.return_value = True

        result, new_task = await manager.handle_disconnected(mock_connect, mock_task)

        assert result is True
        assert new_task is not mock_task

    @pytest.mark.asyncio
    async def test_logs_reconnection_info(self) -> None:
        """Logs info about reconnection."""
        mock_logger = MagicMock()
        manager = ReconnectionManager("test_service", mock_logger)

        mock_connect = AsyncMock()

        await manager.handle_disconnected(mock_connect, None)

        assert mock_logger.info.call_count >= 1
