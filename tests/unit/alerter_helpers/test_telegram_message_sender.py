"""Tests for telegram_message_sender module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from common.alerter_helpers.telegram_message_sender import TelegramMessageSender
from common.alerting import TelegramDeliveryResult


@pytest.fixture
def mock_telegram_client() -> MagicMock:
    """Create a mock Telegram client."""
    client = MagicMock()
    client.send_message = AsyncMock(return_value=(True, None))
    return client


@pytest.fixture
def mock_backoff_manager() -> MagicMock:
    """Create a mock backoff manager."""
    manager = MagicMock()
    manager.should_skip_operation = MagicMock(return_value=False)
    manager.record_failure = MagicMock()
    manager.clear_backoff = MagicMock()
    return manager


class TestTelegramMessageSender:
    """Tests for TelegramMessageSender class."""

    def test_init(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test TelegramMessageSender initialization."""
        sender = TelegramMessageSender(mock_telegram_client, 30, mock_backoff_manager)

        assert sender.telegram_client is mock_telegram_client
        assert sender.timeout_seconds == 30
        assert sender.backoff_manager is mock_backoff_manager

    @pytest.mark.asyncio
    async def test_send_message_success(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test successful message sending."""
        sender = TelegramMessageSender(mock_telegram_client, 30, mock_backoff_manager)

        result = await sender.send_message("Test message", ["123"])

        assert result.success is True
        assert result.failed_recipients == []
        mock_telegram_client.send_message.assert_called_once_with("123", "Test message")
        mock_backoff_manager.clear_backoff.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_multiple_recipients(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test sending to multiple recipients."""
        sender = TelegramMessageSender(mock_telegram_client, 30, mock_backoff_manager)

        result = await sender.send_message("Test message", ["123", "456"])

        assert result.success is True
        assert mock_telegram_client.send_message.call_count == 2
        assert mock_backoff_manager.clear_backoff.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_no_recipients(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test error when no recipients provided."""
        sender = TelegramMessageSender(mock_telegram_client, 30, mock_backoff_manager)

        with pytest.raises(ValueError, match="at least one recipient"):
            await sender.send_message("Test message", [])

    @pytest.mark.asyncio
    async def test_send_message_backoff_active(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test skipping when backoff is active."""
        mock_backoff_manager.should_skip_operation.return_value = True
        sender = TelegramMessageSender(mock_telegram_client, 30, mock_backoff_manager)

        result = await sender.send_message("Test message", ["123"])

        assert result.success is False
        assert result.failed_recipients == ["123"]
        mock_telegram_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_timeout_error(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test handling timeout error."""
        mock_telegram_client.send_message = AsyncMock(side_effect=asyncio.TimeoutError())
        sender = TelegramMessageSender(mock_telegram_client, 30, mock_backoff_manager)

        with pytest.raises(RuntimeError, match="timeout"):
            await sender.send_message("Test message", ["123"])

        mock_backoff_manager.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_client_error(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test handling client error."""
        mock_telegram_client.send_message = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
        sender = TelegramMessageSender(mock_telegram_client, 30, mock_backoff_manager)

        with pytest.raises(RuntimeError, match="failed"):
            await sender.send_message("Test message", ["123"])

        mock_backoff_manager.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_api_failure(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test handling API failure response."""
        mock_telegram_client.send_message = AsyncMock(return_value=(False, "Rate limited"))
        sender = TelegramMessageSender(mock_telegram_client, 30, mock_backoff_manager)

        with pytest.raises(RuntimeError, match="Rate limited"):
            await sender.send_message("Test message", ["123"])

        mock_backoff_manager.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_api_failure_no_error_text(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test handling API failure without error text."""
        mock_telegram_client.send_message = AsyncMock(return_value=(False, None))
        sender = TelegramMessageSender(mock_telegram_client, 30, mock_backoff_manager)

        with pytest.raises(RuntimeError, match="unknown error"):
            await sender.send_message("Test message", ["123"])
