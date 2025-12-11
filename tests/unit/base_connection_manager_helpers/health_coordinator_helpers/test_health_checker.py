"""Tests for health checker module."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.base_connection_manager_helpers.health_coordinator_helpers.health_checker import (
    HealthChecker,
)
from common.connection_state import ConnectionState


class TestHealthCheckerInit:
    """Tests for HealthChecker initialization."""

    def test_init_stores_dependencies(self) -> None:
        """Initialization stores all dependencies."""
        mock_state_manager = MagicMock()
        mock_logger = MagicMock()

        checker = HealthChecker("test_service", mock_state_manager, mock_logger)

        assert checker.service_name == "test_service"
        assert checker.state_manager is mock_state_manager
        assert checker.logger is mock_logger


class TestHealthCheckerCheckAndHandleFailure:
    """Tests for HealthChecker.check_and_handle_failure."""

    @pytest.mark.asyncio
    async def test_returns_true_when_healthy(self) -> None:
        """Returns (True, task) when health check passes."""
        mock_state_manager = MagicMock()
        mock_logger = MagicMock()
        checker = HealthChecker("test_service", mock_state_manager, mock_logger)

        mock_check = AsyncMock(return_value=MagicMock(healthy=True))
        mock_connect = AsyncMock()
        mock_task = MagicMock()

        result, task = await checker.check_and_handle_failure(mock_check, mock_connect, mock_task)

        assert result is True
        assert task is mock_task
        mock_state_manager.transition_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_transitions_state_when_unhealthy(self) -> None:
        """Transitions to DISCONNECTED when health check fails."""
        mock_state_manager = MagicMock()
        mock_logger = MagicMock()
        checker = HealthChecker("test_service", mock_state_manager, mock_logger)

        mock_check = AsyncMock(return_value=MagicMock(healthy=False))
        mock_connect = AsyncMock()
        mock_task = MagicMock()
        mock_task.done.return_value = False

        result, _ = await checker.check_and_handle_failure(mock_check, mock_connect, mock_task)

        assert result is True
        mock_state_manager.transition_state.assert_called_once_with(ConnectionState.DISCONNECTED, "Health check failed")

    @pytest.mark.asyncio
    async def test_starts_reconnection_when_task_done(self) -> None:
        """Starts new reconnection task when current task is done."""
        mock_state_manager = MagicMock()
        mock_logger = MagicMock()
        checker = HealthChecker("test_service", mock_state_manager, mock_logger)

        mock_check = AsyncMock(return_value=MagicMock(healthy=False))
        mock_connect = AsyncMock()
        mock_task = MagicMock()
        mock_task.done.return_value = True

        _, new_task = await checker.check_and_handle_failure(mock_check, mock_connect, mock_task)

        assert new_task is not mock_task

    @pytest.mark.asyncio
    async def test_keeps_existing_task_when_running(self) -> None:
        """Keeps existing task when it's still running."""
        mock_state_manager = MagicMock()
        mock_logger = MagicMock()
        checker = HealthChecker("test_service", mock_state_manager, mock_logger)

        mock_check = AsyncMock(return_value=MagicMock(healthy=False))
        mock_connect = AsyncMock()
        mock_task = MagicMock()
        mock_task.done.return_value = False

        _, new_task = await checker.check_and_handle_failure(mock_check, mock_connect, mock_task)

        assert new_task is mock_task
