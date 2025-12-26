"""Tests for websocket.connection_health_monitor_helpers.alert_sender module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.websocket.connection_health_monitor_helpers.alert_sender import (
    HealthAlertSender,
)


class TestHealthAlertSenderInit:
    """Tests for HealthAlertSender initialization."""

    def test_stores_service_name(self) -> None:
        """Test stores service name."""
        sender = HealthAlertSender("kalshi")
        assert sender.service_name == "kalshi"

    def test_creates_instance(self) -> None:
        """Test creates instance."""
        sender = HealthAlertSender("test_service")
        assert sender is not None


class TestHealthAlertSenderSendHealthAlert:
    """Tests for send_health_alert method."""

    @pytest.mark.asyncio
    async def test_sends_alert_with_message(self) -> None:
        """Test sends alert with formatted message."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock()

        with patch("common.websocket.connection_health_monitor_helpers.alert_sender.Alerter", return_value=mock_alerter):
            sender = HealthAlertSender("kalshi")
            await sender.send_health_alert("Connection lost", "disconnect")

            mock_alerter.send_alert.assert_called_once()
            call_kwargs = mock_alerter.send_alert.call_args[1]
            assert "KALSHI_WS" in call_kwargs["message"]
            assert "Connection lost" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_uses_critical_severity(self) -> None:
        """Test uses CRITICAL severity."""
        from common.alerter import AlertSeverity

        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock()

        with patch("common.websocket.connection_health_monitor_helpers.alert_sender.Alerter", return_value=mock_alerter):
            sender = HealthAlertSender("test")
            await sender.send_health_alert("Test failure", "test_type")

            call_kwargs = mock_alerter.send_alert.call_args[1]
            assert call_kwargs["severity"] == AlertSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_formats_alert_type(self) -> None:
        """Test formats alert type with service name."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock()

        with patch("common.websocket.connection_health_monitor_helpers.alert_sender.Alerter", return_value=mock_alerter):
            sender = HealthAlertSender("kalshi")
            await sender.send_health_alert("Message", "heartbeat")

            call_kwargs = mock_alerter.send_alert.call_args[1]
            assert call_kwargs["alert_type"] == "kalshi_ws_heartbeat"

    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        """Test handles ConnectionError silently."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock(side_effect=ConnectionError("Network error"))

        with patch("common.websocket.connection_health_monitor_helpers.alert_sender.Alerter", return_value=mock_alerter):
            sender = HealthAlertSender("test")
            # Should not raise
            await sender.send_health_alert("Test", "type")

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self) -> None:
        """Test handles TimeoutError silently."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock(side_effect=TimeoutError("Timed out"))

        with patch("common.websocket.connection_health_monitor_helpers.alert_sender.Alerter", return_value=mock_alerter):
            sender = HealthAlertSender("test")
            # Should not raise
            await sender.send_health_alert("Test", "type")

    @pytest.mark.asyncio
    async def test_handles_runtime_error(self) -> None:
        """Test handles RuntimeError silently."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock(side_effect=RuntimeError("Runtime error"))

        with patch("common.websocket.connection_health_monitor_helpers.alert_sender.Alerter", return_value=mock_alerter):
            sender = HealthAlertSender("test")
            # Should not raise
            await sender.send_health_alert("Test", "type")

    @pytest.mark.asyncio
    async def test_message_includes_red_circle_emoji(self) -> None:
        """Test message includes red circle emoji."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock()

        with patch("common.websocket.connection_health_monitor_helpers.alert_sender.Alerter", return_value=mock_alerter):
            sender = HealthAlertSender("service")
            await sender.send_health_alert("Error message", "error")

            call_kwargs = mock_alerter.send_alert.call_args[1]
            assert "🔴" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_message_includes_health_check_failed(self) -> None:
        """Test message includes 'Health check failed' text."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock()

        with patch("common.websocket.connection_health_monitor_helpers.alert_sender.Alerter", return_value=mock_alerter):
            sender = HealthAlertSender("service")
            await sender.send_health_alert("Custom message", "type")

            call_kwargs = mock_alerter.send_alert.call_args[1]
            assert "Health check failed" in call_kwargs["message"]
