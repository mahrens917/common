"""Tests for alerter_helpers.telegram_update_processor module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.alerter_helpers.telegram_update_processor import (
    DEFAULT_TELEGRAM_MESSAGE_TEXT,
    TelegramUpdateProcessor,
)


class TestConstants:
    """Tests for module constants."""

    def test_default_message_text(self) -> None:
        """Test DEFAULT_TELEGRAM_MESSAGE_TEXT is empty."""
        assert DEFAULT_TELEGRAM_MESSAGE_TEXT == ""


class TestTelegramUpdateProcessorInit:
    """Tests for TelegramUpdateProcessor initialization."""

    def test_stores_dependencies(self) -> None:
        """Test initialization stores dependencies."""
        mock_auth_checker = MagicMock()
        mock_registry = MagicMock()
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = MagicMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)

        assert processor.authorization_checker == mock_auth_checker
        assert processor.handler_registry == mock_registry
        assert processor.command_queue == mock_queue
        assert processor.send_alert_callback == mock_send_alert
        assert processor.last_update_id == 0


class TestTelegramUpdateProcessorProcessUpdate:
    """Tests for process_update method."""

    @pytest.mark.asyncio
    async def test_updates_last_update_id(self) -> None:
        """Test updates last_update_id from update."""
        mock_auth_checker = MagicMock()
        mock_registry = MagicMock()
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = MagicMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)

        update = {"update_id": 12345}
        await processor.process_update(update)

        assert processor.last_update_id == 12345

    @pytest.mark.asyncio
    async def test_ignores_non_dict_message(self) -> None:
        """Test ignores update without dict message."""
        mock_auth_checker = MagicMock()
        mock_registry = MagicMock()
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = MagicMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)

        update = {"update_id": 123, "message": "not a dict"}
        await processor.process_update(update)

        assert mock_queue.empty()

    @pytest.mark.asyncio
    async def test_ignores_non_command_text(self) -> None:
        """Test ignores text not starting with /."""
        mock_auth_checker = MagicMock()
        mock_registry = MagicMock()
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = MagicMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)

        update = {"update_id": 123, "message": {"text": "hello"}}
        await processor.process_update(update)

        assert mock_queue.empty()

    @pytest.mark.asyncio
    async def test_handles_unauthorized_user(self) -> None:
        """Test handles unauthorized user."""
        mock_auth_checker = MagicMock()
        mock_auth_checker.is_authorized_user.return_value = False
        mock_registry = MagicMock()
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = AsyncMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)
        processor.unauthorized_handler.handle_unauthorized_attempt = AsyncMock()

        update = {"update_id": 123, "message": {"text": "/help", "from": {"id": 999}}}
        await processor.process_update(update)

        processor.unauthorized_handler.handle_unauthorized_attempt.assert_called_once()
        assert mock_queue.empty()

    @pytest.mark.asyncio
    async def test_queues_authorized_command(self) -> None:
        """Test queues authorized command."""
        mock_auth_checker = MagicMock()
        mock_auth_checker.is_authorized_user.return_value = True
        mock_registry = MagicMock()
        mock_registry.has_handler.return_value = True
        mock_handler = AsyncMock()
        mock_registry.get_handler.return_value = mock_handler
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = MagicMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)

        update = {"update_id": 123, "message": {"text": "/help", "from": {"id": 123}}}
        await processor.process_update(update)

        assert not mock_queue.empty()
        queued = await mock_queue.get()
        assert queued.command == "help"

    @pytest.mark.asyncio
    async def test_extracts_command_from_text(self) -> None:
        """Test extracts command from text with arguments."""
        mock_auth_checker = MagicMock()
        mock_auth_checker.is_authorized_user.return_value = True
        mock_registry = MagicMock()
        mock_registry.has_handler.return_value = True
        mock_registry.get_handler.return_value = AsyncMock()
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = MagicMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)

        update = {"update_id": 123, "message": {"text": "/load 24h", "from": {"id": 123}}}
        await processor.process_update(update)

        queued = await mock_queue.get()
        assert queued.command == "load"

    @pytest.mark.asyncio
    async def test_ignores_unknown_command(self) -> None:
        """Test ignores command without handler."""
        mock_auth_checker = MagicMock()
        mock_auth_checker.is_authorized_user.return_value = True
        mock_registry = MagicMock()
        mock_registry.has_handler.return_value = False
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = MagicMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)

        update = {"update_id": 123, "message": {"text": "/unknown", "from": {"id": 123}}}
        await processor.process_update(update)

        assert mock_queue.empty()

    @pytest.mark.asyncio
    async def test_handles_non_string_text(self) -> None:
        """Test handles non-string text field."""
        mock_auth_checker = MagicMock()
        mock_registry = MagicMock()
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = MagicMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)

        update = {"update_id": 123, "message": {"text": 12345}}
        await processor.process_update(update)

        # Non-string text defaults to empty, which doesn't start with /
        assert mock_queue.empty()


class TestTelegramUpdateProcessorQueueAuthorizedCommand:
    """Tests for _queue_authorized_command method."""

    @pytest.mark.asyncio
    async def test_returns_early_if_no_handler(self) -> None:
        """Test returns early if handler is None."""
        mock_auth_checker = MagicMock()
        mock_registry = MagicMock()
        mock_registry.get_handler.return_value = None
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = MagicMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)

        await processor._queue_authorized_command("help", {"from": {"id": 123}})

        assert mock_queue.empty()

    @pytest.mark.asyncio
    async def test_queues_command_with_timestamp(self) -> None:
        """Test queues command with timestamp."""
        mock_auth_checker = MagicMock()
        mock_registry = MagicMock()
        mock_handler = AsyncMock()
        mock_registry.get_handler.return_value = mock_handler
        mock_queue: asyncio.Queue = asyncio.Queue()
        mock_send_alert = MagicMock()

        processor = TelegramUpdateProcessor(mock_auth_checker, mock_registry, mock_queue, mock_send_alert)

        with patch("common.alerter_helpers.telegram_update_processor.time.time", return_value=1000.0):
            await processor._queue_authorized_command("help", {"from": {"id": 123}})

        queued = await mock_queue.get()
        assert queued.command == "help"
        assert queued.handler == mock_handler
        assert queued.timestamp == 1000.0
