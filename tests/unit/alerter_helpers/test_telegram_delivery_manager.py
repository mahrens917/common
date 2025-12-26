"""Tests for alerter_helpers.telegram_delivery_manager module."""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from common.alerter_helpers.telegram_delivery_manager import (
    ERR_NO_RECIPIENTS,
    TELEGRAM_METHOD_DOCUMENT,
    TELEGRAM_METHOD_PHOTO,
    TelegramDeliveryManager,
    _get_image_properties,
)
from common.alerting import Alert, AlertSeverity, TelegramDeliveryResult


class TestConstants:
    """Tests for module constants."""

    def test_err_no_recipients(self) -> None:
        """Test ERR_NO_RECIPIENTS constant."""
        assert "recipient" in ERR_NO_RECIPIENTS.lower()

    def test_telegram_method_photo(self) -> None:
        """Test TELEGRAM_METHOD_PHOTO constant."""
        assert TELEGRAM_METHOD_PHOTO == "sendPhoto"

    def test_telegram_method_document(self) -> None:
        """Test TELEGRAM_METHOD_DOCUMENT constant."""
        assert TELEGRAM_METHOD_DOCUMENT == "sendDocument"


class TestGetImageProperties:
    """Tests for _get_image_properties function."""

    def test_png_is_photo(self) -> None:
        """Test PNG file is photo."""
        name, is_photo = _get_image_properties("/path/to/image.png")

        assert name == "image.png"
        assert is_photo is True

    def test_jpg_is_photo(self) -> None:
        """Test JPG file is photo."""
        name, is_photo = _get_image_properties("/path/to/image.jpg")

        assert name == "image.jpg"
        assert is_photo is True

    def test_jpeg_is_photo(self) -> None:
        """Test JPEG file is photo."""
        name, is_photo = _get_image_properties("/path/to/image.jpeg")

        assert name == "image.jpeg"
        assert is_photo is True

    def test_webp_is_photo(self) -> None:
        """Test WEBP file is photo."""
        name, is_photo = _get_image_properties("/path/to/image.webp")

        assert name == "image.webp"
        assert is_photo is True

    def test_pdf_is_document(self) -> None:
        """Test PDF file is document."""
        name, is_photo = _get_image_properties("/path/to/file.pdf")

        assert name == "file.pdf"
        assert is_photo is False

    def test_gif_is_document(self) -> None:
        """Test GIF file is document."""
        name, is_photo = _get_image_properties("/path/to/image.gif")

        assert name == "image.gif"
        assert is_photo is False

    def test_uppercase_extension(self) -> None:
        """Test uppercase extension is handled."""
        name, is_photo = _get_image_properties("/path/to/IMAGE.PNG")

        assert name == "IMAGE.PNG"
        assert is_photo is True


class TestTelegramDeliveryManagerInit:
    """Tests for TelegramDeliveryManager initialization."""

    def test_stores_dependencies(self) -> None:
        """Test initialization stores dependencies."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)

        assert manager.message_sender == mock_message_sender
        assert manager.media_sender == mock_media_sender
        assert manager.alert_formatter == mock_formatter


class TestTelegramDeliveryManagerSendAlert:
    """Tests for send_alert method."""

    @pytest.mark.asyncio
    async def test_sends_alert_successfully(self) -> None:
        """Test sends alert successfully."""
        mock_message_sender = MagicMock()
        mock_message_sender.send_message = AsyncMock(
            return_value=TelegramDeliveryResult(success=True, failed_recipients=[], queued_recipients=[])
        )
        mock_media_sender = MagicMock()
        mock_formatter = MagicMock()
        mock_formatter.format_telegram_message.return_value = "Formatted alert"

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)
        alert = Alert(message="Test message", severity=AlertSeverity.CRITICAL, timestamp=time.time(), alert_type="test")
        recipients = ["123456789"]

        result = await manager.send_alert(alert, recipients)

        assert result.success is True
        mock_formatter.format_telegram_message.assert_called_once_with(alert)
        mock_message_sender.send_message.assert_called_once_with("Formatted alert", recipients)

    @pytest.mark.asyncio
    async def test_raises_on_empty_recipients(self) -> None:
        """Test raises ValueError on empty recipients."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)
        alert = Alert(message="Test message", severity=AlertSeverity.CRITICAL, timestamp=time.time(), alert_type="test")

        with pytest.raises(ValueError) as exc_info:
            await manager.send_alert(alert, [])

        assert "recipient" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_handles_client_error(self) -> None:
        """Test handles aiohttp ClientError."""
        mock_message_sender = MagicMock()
        mock_message_sender.send_message = AsyncMock(side_effect=aiohttp.ClientError("Connection error"))
        mock_media_sender = MagicMock()
        mock_formatter = MagicMock()
        mock_formatter.format_telegram_message.return_value = "Formatted alert"

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)
        alert = Alert(message="Test message", severity=AlertSeverity.CRITICAL, timestamp=time.time(), alert_type="test")
        recipients = ["123456789"]

        result = await manager.send_alert(alert, recipients)

        assert result.success is False
        assert "123456789" in result.failed_recipients

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self) -> None:
        """Test handles TimeoutError."""
        mock_message_sender = MagicMock()
        mock_message_sender.send_message = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_media_sender = MagicMock()
        mock_formatter = MagicMock()
        mock_formatter.format_telegram_message.return_value = "Formatted alert"

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)
        alert = Alert(message="Test message", severity=AlertSeverity.CRITICAL, timestamp=time.time(), alert_type="test")
        recipients = ["123456789"]

        result = await manager.send_alert(alert, recipients)

        assert result.success is False

    @pytest.mark.asyncio
    async def test_handles_os_error(self) -> None:
        """Test handles OSError."""
        mock_message_sender = MagicMock()
        mock_message_sender.send_message = AsyncMock(side_effect=OSError("OS error"))
        mock_media_sender = MagicMock()
        mock_formatter = MagicMock()
        mock_formatter.format_telegram_message.return_value = "Formatted alert"

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)
        alert = Alert(message="Test message", severity=AlertSeverity.CRITICAL, timestamp=time.time(), alert_type="test")
        recipients = ["123456789"]

        result = await manager.send_alert(alert, recipients)

        assert result.success is False

    @pytest.mark.asyncio
    async def test_handles_failed_delivery_result(self) -> None:
        """Test handles failed delivery result."""
        mock_message_sender = MagicMock()
        mock_message_sender.send_message = AsyncMock(
            return_value=TelegramDeliveryResult(
                success=False, failed_recipients=["123456789"], queued_recipients=[]
            )
        )
        mock_media_sender = MagicMock()
        mock_formatter = MagicMock()
        mock_formatter.format_telegram_message.return_value = "Formatted alert"

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)
        alert = Alert(message="Test message", severity=AlertSeverity.CRITICAL, timestamp=time.time(), alert_type="test")
        recipients = ["123456789"]

        result = await manager.send_alert(alert, recipients)

        assert result.success is False


class TestTelegramDeliveryManagerSendChart:
    """Tests for send_chart method."""

    @pytest.mark.asyncio
    async def test_sends_chart_successfully(self) -> None:
        """Test sends chart successfully."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_media_sender.send_media = AsyncMock(
            return_value=TelegramDeliveryResult(success=True, failed_recipients=[], queued_recipients=[])
        )
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            result = await manager.send_chart(temp_path, "Test caption", ["123456789"])

            assert result is True
            mock_media_sender.send_media.assert_called_once()
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_returns_false_on_empty_recipients(self) -> None:
        """Test returns False on empty recipients."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)
        result = await manager.send_chart("/path/to/image.png", "Caption", [])

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_missing_file(self) -> None:
        """Test returns False when file doesn't exist."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)
        result = await manager.send_chart("/nonexistent/path/image.png", "Caption", ["123456789"])

        assert result is False

    @pytest.mark.asyncio
    async def test_uses_photo_method_for_png(self) -> None:
        """Test uses sendPhoto method for PNG files."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_media_sender.send_media = AsyncMock(
            return_value=TelegramDeliveryResult(success=True, failed_recipients=[], queued_recipients=[])
        )
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            await manager.send_chart(temp_path, "Test caption", ["123456789"])

            call_kwargs = mock_media_sender.send_media.call_args[1]
            assert call_kwargs["is_photo"] is True
            assert call_kwargs["telegram_method"] == "sendPhoto"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_uses_document_method_for_pdf(self) -> None:
        """Test uses sendDocument method for PDF files."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_media_sender.send_media = AsyncMock(
            return_value=TelegramDeliveryResult(success=True, failed_recipients=[], queued_recipients=[])
        )
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf data")
            temp_path = f.name

        try:
            await manager.send_chart(temp_path, "Test caption", ["123456789"])

            call_kwargs = mock_media_sender.send_media.call_args[1]
            assert call_kwargs["is_photo"] is False
            assert call_kwargs["telegram_method"] == "sendDocument"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_handles_client_error(self) -> None:
        """Test handles aiohttp ClientError."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_media_sender.send_media = AsyncMock(side_effect=aiohttp.ClientError("Connection error"))
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            result = await manager.send_chart(temp_path, "Test caption", ["123456789"])

            assert result is False
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self) -> None:
        """Test handles TimeoutError."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_media_sender.send_media = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            result = await manager.send_chart(temp_path, "Test caption", ["123456789"])

            assert result is False
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_handles_failed_delivery_result(self) -> None:
        """Test handles failed delivery result."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_media_sender.send_media = AsyncMock(
            return_value=TelegramDeliveryResult(
                success=False, failed_recipients=["123456789"], queued_recipients=[]
            )
        )
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            result = await manager.send_chart(temp_path, "Test caption", ["123456789"])

            assert result is False
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_uses_caption_for_chart_name(self) -> None:
        """Test uses caption as chart name when provided."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_media_sender.send_media = AsyncMock(side_effect=aiohttp.ClientError("Error"))
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            await manager.send_chart(temp_path, "My Chart", ["123456789"])
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_uses_filename_when_caption_empty(self) -> None:
        """Test uses filename when caption is empty."""
        mock_message_sender = MagicMock()
        mock_media_sender = MagicMock()
        mock_media_sender.send_media = AsyncMock(
            return_value=TelegramDeliveryResult(success=True, failed_recipients=[], queued_recipients=[])
        )
        mock_formatter = MagicMock()

        manager = TelegramDeliveryManager(mock_message_sender, mock_media_sender, mock_formatter)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            await manager.send_chart(temp_path, "  ", ["123456789"])
        finally:
            Path(temp_path).unlink()
