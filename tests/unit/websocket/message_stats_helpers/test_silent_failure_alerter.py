"""Tests for websocket.message_stats_helpers.silent_failure_alerter module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.websocket.message_stats_helpers.silent_failure_alerter import (
    check_silent_failure_threshold,
    send_silent_failure_alert,
)


class TestSendSilentFailureAlert:
    """Tests for send_silent_failure_alert function."""

    @pytest.mark.asyncio
    async def test_sends_alert_with_correct_message(self) -> None:
        """Test sends alert with formatted message."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock()

        with patch("common.alerter.Alerter", return_value=mock_alerter):
            await send_silent_failure_alert("kalshi", 120.5)

            mock_alerter.send_alert.assert_called_once()
            call_kwargs = mock_alerter.send_alert.call_args[1]
            assert "KALSHI_WS" in call_kwargs["message"]
            assert "Silent failure" in call_kwargs["message"]
            assert "120.5" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_uses_critical_severity(self) -> None:
        """Test uses CRITICAL severity."""
        from common.alerter import AlertSeverity

        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock()

        with patch("common.alerter.Alerter", return_value=mock_alerter):
            await send_silent_failure_alert("test", 60.0)

            call_kwargs = mock_alerter.send_alert.call_args[1]
            assert call_kwargs["severity"] == AlertSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_formats_alert_type_correctly(self) -> None:
        """Test formats alert type with service name."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock()

        with patch("common.alerter.Alerter", return_value=mock_alerter):
            await send_silent_failure_alert("kalshi", 90.0)

            call_kwargs = mock_alerter.send_alert.call_args[1]
            assert call_kwargs["alert_type"] == "kalshi_ws_silent_failure"

    @pytest.mark.asyncio
    async def test_handles_runtime_error_silently(self) -> None:
        """Test handles RuntimeError silently."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock(side_effect=RuntimeError("Setup failed"))

        with patch("common.alerter.Alerter", return_value=mock_alerter):
            # Should not raise
            await send_silent_failure_alert("test", 60.0)

    @pytest.mark.asyncio
    async def test_handles_connection_error_silently(self) -> None:
        """Test handles ConnectionError silently."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock(side_effect=ConnectionError("No connection"))

        with patch("common.alerter.Alerter", return_value=mock_alerter):
            # Should not raise
            await send_silent_failure_alert("test", 60.0)

    @pytest.mark.asyncio
    async def test_reraises_cancelled_error(self) -> None:
        """Test reraises CancelledError."""
        mock_alerter = MagicMock()
        mock_alerter.send_alert = AsyncMock(side_effect=asyncio.CancelledError())

        with patch("common.alerter.Alerter", return_value=mock_alerter):
            with pytest.raises(asyncio.CancelledError):
                await send_silent_failure_alert("test", 60.0)


class TestCheckSilentFailureThreshold:
    """Tests for check_silent_failure_threshold function."""

    def test_returns_false_when_current_rate_positive(self) -> None:
        """Test returns False when current rate is positive."""
        result = check_silent_failure_threshold(
            current_rate=10,
            current_time=100.0,
            last_nonzero_update_time=50.0,
            threshold_seconds=30,
            service_name="test",
        )

        assert result is False

    def test_returns_false_when_below_threshold(self) -> None:
        """Test returns False when time since update is below threshold."""
        result = check_silent_failure_threshold(
            current_rate=0,
            current_time=100.0,
            last_nonzero_update_time=90.0,  # 10 seconds ago
            threshold_seconds=30,
            service_name="test",
        )

        assert result is False

    def test_returns_true_when_threshold_exceeded(self) -> None:
        """Test returns True when threshold is exceeded."""
        result = check_silent_failure_threshold(
            current_rate=0,
            current_time=100.0,
            last_nonzero_update_time=50.0,  # 50 seconds ago
            threshold_seconds=30,
            service_name="test",
        )

        assert result is True

    def test_returns_false_at_exact_threshold(self) -> None:
        """Test returns False at exact threshold boundary."""
        result = check_silent_failure_threshold(
            current_rate=0,
            current_time=100.0,
            last_nonzero_update_time=70.0,  # Exactly 30 seconds ago
            threshold_seconds=30,
            service_name="test",
        )

        assert result is False

    def test_returns_true_just_past_threshold(self) -> None:
        """Test returns True just past threshold."""
        result = check_silent_failure_threshold(
            current_rate=0,
            current_time=100.0,
            last_nonzero_update_time=69.9,  # 30.1 seconds ago
            threshold_seconds=30,
            service_name="test",
        )

        assert result is True
