"""Tests for notification handler module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.base_connection_manager_helpers.notification_handler import NotificationHandler
from src.common.connection_state import ConnectionState


class TestNotificationHandlerInit:
    """Tests for NotificationHandler initialization."""

    def test_initializes_with_dependencies(self) -> None:
        """Initializes with all required dependencies."""
        state_mgr = MagicMock()
        metrics = MagicMock()

        handler = NotificationHandler(
            service_name="test_service",
            state_manager=state_mgr,
            metrics_tracker=metrics,
        )

        assert handler.service_name == "test_service"
        assert handler.state_manager is state_mgr
        assert handler.metrics_tracker is metrics


class TestNotificationHandlerSendConnectionNotification:
    """Tests for NotificationHandler.send_connection_notification."""

    @pytest.mark.asyncio
    async def test_broadcasts_ready_state_when_connected(self) -> None:
        """Broadcasts READY state when connected."""
        state_mgr = MagicMock()
        state_mgr._broadcast_state_change = AsyncMock()
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(
            total_connections=1, total_reconnection_attempts=0
        )

        handler = NotificationHandler(
            service_name="test_service",
            state_manager=state_mgr,
            metrics_tracker=metrics,
        )

        await handler.send_connection_notification(True)

        state_mgr._broadcast_state_change.assert_called_once_with(ConnectionState.READY, None)

    @pytest.mark.asyncio
    async def test_broadcasts_reconnecting_state_when_disconnected(self) -> None:
        """Broadcasts RECONNECTING state when disconnected."""
        state_mgr = MagicMock()
        state_mgr._broadcast_state_change = AsyncMock()
        metrics = MagicMock()

        handler = NotificationHandler(
            service_name="test_service",
            state_manager=state_mgr,
            metrics_tracker=metrics,
        )

        await handler.send_connection_notification(False, "Connection lost")

        state_mgr._broadcast_state_change.assert_called_once_with(
            ConnectionState.RECONNECTING, "Connection lost"
        )

    @pytest.mark.asyncio
    async def test_logs_startup_message_on_first_connection(self) -> None:
        """Logs startup message on first connection."""
        state_mgr = MagicMock()
        state_mgr._broadcast_state_change = AsyncMock()
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(
            total_connections=1, total_reconnection_attempts=0
        )

        handler = NotificationHandler(
            service_name="test_service",
            state_manager=state_mgr,
            metrics_tracker=metrics,
        )

        with patch.object(handler.logger, "info") as mock_log:
            await handler.send_connection_notification(True)

        mock_log.assert_called_once()
        assert "Started" in mock_log.call_args[0][0]

    @pytest.mark.asyncio
    async def test_logs_reconnection_message_on_subsequent_connection(self) -> None:
        """Logs reconnection message on subsequent connection."""
        state_mgr = MagicMock()
        state_mgr._broadcast_state_change = AsyncMock()
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(
            total_connections=3, total_reconnection_attempts=5, consecutive_failures=2
        )

        handler = NotificationHandler(
            service_name="test_service",
            state_manager=state_mgr,
            metrics_tracker=metrics,
        )

        with patch.object(handler.logger, "info") as mock_log:
            await handler.send_connection_notification(True)

        mock_log.assert_called_once()
        assert "Re-connected" in mock_log.call_args[0][0]

    @pytest.mark.asyncio
    async def test_logs_warning_on_disconnection(self) -> None:
        """Logs warning on disconnection."""
        state_mgr = MagicMock()
        state_mgr._broadcast_state_change = AsyncMock()
        metrics = MagicMock()

        handler = NotificationHandler(
            service_name="test_service",
            state_manager=state_mgr,
            metrics_tracker=metrics,
        )

        with patch.object(handler.logger, "warning") as mock_log:
            await handler.send_connection_notification(False)

        mock_log.assert_called_once()
        assert "Connection lost" in mock_log.call_args[0][0]

    @pytest.mark.asyncio
    async def test_handles_reconnection_with_one_attempt(self) -> None:
        """Handles edge case where total_reconnection_attempts equals 1."""
        state_mgr = MagicMock()
        state_mgr._broadcast_state_change = AsyncMock()
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(
            total_connections=1, total_reconnection_attempts=1, consecutive_failures=0
        )

        handler = NotificationHandler(
            service_name="test_service",
            state_manager=state_mgr,
            metrics_tracker=metrics,
        )

        with patch.object(handler.logger, "info") as mock_log:
            await handler.send_connection_notification(True)

        mock_log.assert_called_once()
        # This is still considered startup with 1 attempt
        assert "Started" in mock_log.call_args[0][0]
