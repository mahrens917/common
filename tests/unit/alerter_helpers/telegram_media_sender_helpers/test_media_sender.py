"""Tests for media_sender module."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.alerter_helpers.telegram_media_sender_helpers.media_sender import MediaSender


@pytest.fixture
def mock_telegram_client() -> MagicMock:
    """Create a mock Telegram client."""
    client = MagicMock()
    client.send_media = AsyncMock(return_value=(True, None))
    return client


@pytest.fixture
def mock_backoff_manager() -> MagicMock:
    """Create a mock backoff manager."""
    manager = MagicMock()
    manager.record_failure = MagicMock()
    manager.clear_backoff = MagicMock()
    return manager


class TestMediaSender:
    """Tests for MediaSender class."""

    def test_init(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test MediaSender initialization."""
        sender = MediaSender(mock_telegram_client, 30, mock_backoff_manager)

        assert sender.telegram_client is mock_telegram_client
        assert sender.timeout_seconds == 30
        assert sender.backoff_manager is mock_backoff_manager

    @pytest.mark.asyncio
    async def test_send_to_all_success(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test successful media send to all recipients."""
        sender = MediaSender(mock_telegram_client, 30, mock_backoff_manager)
        recipients = ["user1", "user2"]
        payload_path = Path("/path/to/image.png")

        result = await sender.send_to_all(
            recipients=recipients,
            payload_path=payload_path,
            caption="Test caption",
            is_photo=True,
            telegram_method="sendPhoto",
        )

        assert result == 2
        assert mock_telegram_client.send_media.call_count == 2
        assert mock_backoff_manager.clear_backoff.call_count == 2

    @pytest.mark.asyncio
    async def test_send_to_all_single_recipient(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test media send to single recipient."""
        sender = MediaSender(mock_telegram_client, 30, mock_backoff_manager)
        payload_path = Path("/path/to/document.pdf")

        result = await sender.send_to_all(
            recipients=["user1"],
            payload_path=payload_path,
            caption="Document",
            is_photo=False,
            telegram_method="sendDocument",
        )

        assert result == 1
        mock_telegram_client.send_media.assert_called_once_with(
            "user1",
            payload_path,
            caption="Document",
            is_photo=False,
            method="sendDocument",
        )

    @pytest.mark.asyncio
    async def test_send_to_recipient_timeout(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test handling timeout during send."""
        mock_telegram_client.send_media = AsyncMock(side_effect=asyncio.TimeoutError())
        sender = MediaSender(mock_telegram_client, 30, mock_backoff_manager)

        with pytest.raises(RuntimeError, match="timeout"):
            await sender.send_to_all(
                recipients=["user1"],
                payload_path=Path("/path/to/image.png"),
                caption="Test",
                is_photo=True,
                telegram_method="sendPhoto",
            )

        mock_backoff_manager.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_recipient_os_error(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test handling OSError during send."""
        mock_telegram_client.send_media = AsyncMock(side_effect=OSError("File not found"))
        sender = MediaSender(mock_telegram_client, 30, mock_backoff_manager)

        with pytest.raises(RuntimeError, match="failed"):
            await sender.send_to_all(
                recipients=["user1"],
                payload_path=Path("/path/to/image.png"),
                caption="Test",
                is_photo=True,
                telegram_method="sendPhoto",
            )

        mock_backoff_manager.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_recipient_api_failure(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test handling API failure response."""
        mock_telegram_client.send_media = AsyncMock(return_value=(False, "Rate limited"))
        sender = MediaSender(mock_telegram_client, 30, mock_backoff_manager)

        with pytest.raises(RuntimeError, match="Rate limited"):
            await sender.send_to_all(
                recipients=["user1"],
                payload_path=Path("/path/to/image.png"),
                caption="Test",
                is_photo=True,
                telegram_method="sendPhoto",
            )

        mock_backoff_manager.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_recipient_api_failure_no_error_text(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test handling API failure without error text."""
        mock_telegram_client.send_media = AsyncMock(return_value=(False, None))
        sender = MediaSender(mock_telegram_client, 30, mock_backoff_manager)

        with pytest.raises(RuntimeError, match="unknown error"):
            await sender.send_to_all(
                recipients=["user1"],
                payload_path=Path("/path/to/image.png"),
                caption="Test",
                is_photo=True,
                telegram_method="sendPhoto",
            )

    @pytest.mark.asyncio
    async def test_send_to_all_empty_recipients(
        self,
        mock_telegram_client: MagicMock,
        mock_backoff_manager: MagicMock,
    ) -> None:
        """Test media send with empty recipients list."""
        sender = MediaSender(mock_telegram_client, 30, mock_backoff_manager)

        result = await sender.send_to_all(
            recipients=[],
            payload_path=Path("/path/to/image.png"),
            caption="Test",
            is_photo=True,
            telegram_method="sendPhoto",
        )

        assert result == 0
        mock_telegram_client.send_media.assert_not_called()
