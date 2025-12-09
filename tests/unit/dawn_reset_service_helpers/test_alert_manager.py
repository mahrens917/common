"""Tests for alert manager module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.dawn_reset_service_helpers.alert_manager import AlertManager


class TestAlertManagerInit:
    """Tests for AlertManager initialization."""

    def test_initializes_with_telegram_handler(self) -> None:
        """Initializes with telegram handler."""
        handler = MagicMock()

        manager = AlertManager(telegram_handler=handler)

        assert manager.telegram_handler is handler

    def test_initializes_without_telegram_handler(self) -> None:
        """Initializes without telegram handler."""
        manager = AlertManager()

        assert manager.telegram_handler is None

    def test_initializes_empty_reset_status(self) -> None:
        """Initializes with empty reset status dict."""
        manager = AlertManager()

        assert manager._last_reset_status == {}


class TestAlertManagerSendResetAlert:
    """Tests for AlertManager.send_reset_alert."""

    @pytest.mark.asyncio
    async def test_returns_early_when_no_handler(self) -> None:
        """Returns early when no telegram handler."""
        manager = AlertManager()

        await manager.send_reset_alert("KJFK", "max_temp_f", True, 65.0, 70.0)

    @pytest.mark.asyncio
    async def test_returns_early_when_status_unchanged(self) -> None:
        """Returns early when status unchanged (non-max_temp_f)."""
        handler = MagicMock()
        handler.send_custom_message = AsyncMock()
        manager = AlertManager(telegram_handler=handler)
        manager._last_reset_status["KJFK:some_field"] = True

        await manager.send_reset_alert("KJFK", "some_field", True, 65.0, 70.0)

        handler.send_custom_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_alert_for_max_temp_f_reset(self) -> None:
        """Sends alert for max_temp_f reset."""
        handler = MagicMock()
        handler.send_custom_message = AsyncMock()
        manager = AlertManager(telegram_handler=handler)

        await manager.send_reset_alert("KJFK", "max_temp_f", True, 65.0, 70.0)

        handler.send_custom_message.assert_called_once()
        call_args = handler.send_custom_message.call_args[0][0]
        assert "DAWN RESET SUCCESS" in call_args
        assert "KJFK" in call_args
        assert "max_temp_f" in call_args
        assert "65.0" in call_args
        assert "70.0" in call_args

    @pytest.mark.asyncio
    async def test_sends_alert_for_other_field_reset(self) -> None:
        """Sends alert for other field reset."""
        handler = MagicMock()
        handler.send_custom_message = AsyncMock()
        manager = AlertManager(telegram_handler=handler)

        await manager.send_reset_alert("KJFK", "t_yes_bid", True, 50.0, None)

        handler.send_custom_message.assert_called_once()
        call_args = handler.send_custom_message.call_args[0][0]
        assert "DAWN RESET" in call_args
        assert "KJFK" in call_args
        assert "t_yes_bid" in call_args

    @pytest.mark.asyncio
    async def test_does_not_send_when_not_reset(self) -> None:
        """Does not send notification when not reset."""
        handler = MagicMock()
        handler.send_custom_message = AsyncMock()
        manager = AlertManager(telegram_handler=handler)

        await manager.send_reset_alert("KJFK", "max_temp_f", False, 65.0, 70.0)

        handler.send_custom_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_last_reset_status(self) -> None:
        """Updates last reset status after sending."""
        handler = MagicMock()
        handler.send_custom_message = AsyncMock()
        manager = AlertManager(telegram_handler=handler)

        await manager.send_reset_alert("KJFK", "max_temp_f", True, 65.0, 70.0)

        assert manager._last_reset_status["KJFK:max_temp_f"] is True

    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        """Handles ConnectionError gracefully."""
        handler = MagicMock()
        handler.send_custom_message = AsyncMock(side_effect=ConnectionError("Network error"))
        manager = AlertManager(telegram_handler=handler)

        with patch("src.common.dawn_reset_service_helpers.alert_manager.logger"):
            await manager.send_reset_alert("KJFK", "max_temp_f", True, 65.0, 70.0)

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self) -> None:
        """Handles TimeoutError gracefully."""
        handler = MagicMock()
        handler.send_custom_message = AsyncMock(side_effect=TimeoutError("Timeout"))
        manager = AlertManager(telegram_handler=handler)

        with patch("src.common.dawn_reset_service_helpers.alert_manager.logger"):
            await manager.send_reset_alert("KJFK", "max_temp_f", True, 65.0, 70.0)

    @pytest.mark.asyncio
    async def test_always_sends_for_max_temp_f_even_when_same_status(self) -> None:
        """Always sends alert for max_temp_f reset even when status is same."""
        handler = MagicMock()
        handler.send_custom_message = AsyncMock()
        manager = AlertManager(telegram_handler=handler)
        manager._last_reset_status["KJFK:max_temp_f"] = True

        await manager.send_reset_alert("KJFK", "max_temp_f", True, 65.0, 70.0)

        handler.send_custom_message.assert_called_once()
