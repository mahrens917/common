"""Tests for alerter_helpers.telegram_media_sender module."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from common.alerter_helpers.telegram_media_sender import (
    BackoffGuardMixin,
    DeliveryMixin,
    PayloadResolutionMixin,
    RecipientValidationMixin,
    TelegramMediaSender,
)

# Test constants
TEST_TIMEOUT_SECONDS = 30.0
TEST_EXPECTED_RECIPIENT_COUNT = 2


class TestRecipientValidationMixin:
    """Tests for RecipientValidationMixin."""

    def test_raises_on_empty_recipients(self) -> None:
        """Test raises ValueError on empty recipients."""
        mixin = RecipientValidationMixin()

        with pytest.raises(ValueError) as exc_info:
            mixin._assert_recipients([])

        assert "recipient" in str(exc_info.value).lower()

    def test_passes_with_recipients(self) -> None:
        """Test passes with valid recipients."""
        mixin = RecipientValidationMixin()

        # Should not raise
        mixin._assert_recipients(["123", "456"])


class TestPayloadResolutionMixin:
    """Tests for PayloadResolutionMixin."""

    def test_uses_spooled_path_when_provided(self) -> None:
        """Test uses spooled path when provided."""
        mixin = PayloadResolutionMixin()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            spooled_path = Path(f.name)

        try:
            result = mixin._resolve_payload_path(Path("/source"), spooled_path)
            assert result == spooled_path
        finally:
            spooled_path.unlink()

    def test_uses_source_path_when_no_spooled(self) -> None:
        """Test uses source path when no spooled path."""
        mixin = PayloadResolutionMixin()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            source_path = Path(f.name)

        try:
            result = mixin._resolve_payload_path(source_path, None)
            assert result == source_path
        finally:
            source_path.unlink()

    def test_raises_on_missing_file(self) -> None:
        """Test raises FileNotFoundError on missing file."""
        mixin = PayloadResolutionMixin()

        with pytest.raises(FileNotFoundError):
            mixin._resolve_payload_path(Path("/nonexistent/path"), None)


class TestBackoffGuardMixin:
    """Tests for BackoffGuardMixin."""

    def test_raises_when_backoff_active(self) -> None:
        """Test raises RuntimeError when backoff active."""

        class TestMixin(BackoffGuardMixin):
            pass

        mixin = TestMixin()
        mixin.backoff_manager = MagicMock()
        mixin.backoff_manager.should_skip_operation.return_value = True

        with pytest.raises(RuntimeError) as exc_info:
            mixin._ensure_backoff_allowance("sendPhoto")

        assert "backoff" in str(exc_info.value).lower()

    def test_passes_when_no_backoff(self) -> None:
        """Test passes when no backoff active."""

        class TestMixin(BackoffGuardMixin):
            pass

        mixin = TestMixin()
        mixin.backoff_manager = MagicMock()
        mixin.backoff_manager.should_skip_operation.return_value = False

        # Should not raise
        mixin._ensure_backoff_allowance("sendPhoto")


class TestDeliveryMixin:
    """Tests for DeliveryMixin."""

    @pytest.mark.asyncio
    async def test_delivers_to_all_recipients(self) -> None:
        """Test delivers to all recipients."""

        class TestMixin(DeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.telegram_client = MagicMock()
        mixin.telegram_client.send_media = AsyncMock(return_value=(True, None))
        mixin.timeout_seconds = TEST_TIMEOUT_SECONDS
        mixin.backoff_manager = MagicMock()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            count = await mixin._deliver_to_recipients(["user1", "user2"], path, "caption", True, "sendPhoto")

            assert count == TEST_EXPECTED_RECIPIENT_COUNT
            assert mixin.telegram_client.send_media.call_count == TEST_EXPECTED_RECIPIENT_COUNT
        finally:
            path.unlink()

    @pytest.mark.asyncio
    async def test_clears_backoff_on_success(self) -> None:
        """Test clears backoff on successful send."""

        class TestMixin(DeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.telegram_client = MagicMock()
        mixin.telegram_client.send_media = AsyncMock(return_value=(True, None))
        mixin.timeout_seconds = TEST_TIMEOUT_SECONDS
        mixin.backoff_manager = MagicMock()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            await mixin._send_to_single_recipient("user1", path, "caption", True, "sendPhoto")

            mixin.backoff_manager.clear_backoff.assert_called_once()
        finally:
            path.unlink()

    @pytest.mark.asyncio
    async def test_records_failure_on_error(self) -> None:
        """Test records failure when send fails."""

        class TestMixin(DeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.telegram_client = MagicMock()
        mixin.telegram_client.send_media = AsyncMock(return_value=(False, "Error message"))
        mixin.timeout_seconds = TEST_TIMEOUT_SECONDS
        mixin.backoff_manager = MagicMock()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            with pytest.raises(RuntimeError):
                await mixin._send_to_single_recipient("user1", path, "caption", True, "sendPhoto")

            mixin.backoff_manager.record_failure.assert_called_once()
        finally:
            path.unlink()

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self) -> None:
        """Test handles asyncio.TimeoutError."""

        class TestMixin(DeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.telegram_client = MagicMock()
        mixin.telegram_client.send_media = AsyncMock(side_effect=asyncio.TimeoutError())
        mixin.timeout_seconds = TEST_TIMEOUT_SECONDS
        mixin.backoff_manager = MagicMock()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            with pytest.raises(RuntimeError) as exc_info:
                await mixin._attempt_send("user1", path, "caption", True, "sendPhoto")

            assert "timeout" in str(exc_info.value).lower()
            mixin.backoff_manager.record_failure.assert_called_once()
        finally:
            path.unlink()

    @pytest.mark.asyncio
    async def test_handles_client_error(self) -> None:
        """Test handles aiohttp.ClientError."""

        class TestMixin(DeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.telegram_client = MagicMock()
        mixin.telegram_client.send_media = AsyncMock(side_effect=aiohttp.ClientError())
        mixin.timeout_seconds = TEST_TIMEOUT_SECONDS
        mixin.backoff_manager = MagicMock()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            with pytest.raises(RuntimeError):
                await mixin._attempt_send("user1", path, "caption", True, "sendPhoto")

            mixin.backoff_manager.record_failure.assert_called_once()
        finally:
            path.unlink()


class TestTelegramMediaSenderInit:
    """Tests for TelegramMediaSender initialization."""

    def test_stores_dependencies(self) -> None:
        """Test initialization stores dependencies."""
        mock_client = MagicMock()
        mock_backoff = MagicMock()

        sender = TelegramMediaSender(mock_client, 30, mock_backoff)

        assert sender.telegram_client == mock_client
        assert sender.timeout_seconds == 30
        assert sender.backoff_manager == mock_backoff


class TestTelegramMediaSenderSendMedia:
    """Tests for send_media method."""

    @pytest.mark.asyncio
    async def test_raises_on_empty_recipients(self) -> None:
        """Test raises ValueError on empty recipients."""
        mock_client = MagicMock()
        mock_backoff = MagicMock()

        sender = TelegramMediaSender(mock_client, 30, mock_backoff)

        with pytest.raises(ValueError):
            await sender.send_media(Path("/test"), "caption", [], True, "sendPhoto")

    @pytest.mark.asyncio
    async def test_returns_failure_when_backoff_active(self) -> None:
        """Test returns failure result when backoff active."""
        mock_client = MagicMock()
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = True

        sender = TelegramMediaSender(mock_client, 30, mock_backoff)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            result = await sender.send_media(path, "caption", ["user1"], True, "sendPhoto")

            assert result.success is False
            assert "user1" in result.failed_recipients
        finally:
            path.unlink()

    @pytest.mark.asyncio
    async def test_sends_successfully(self) -> None:
        """Test sends media successfully."""
        mock_client = MagicMock()
        mock_client.send_media = AsyncMock(return_value=(True, None))
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = False

        sender = TelegramMediaSender(mock_client, 30, mock_backoff)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            result = await sender.send_media(path, "caption", ["user1"], True, "sendPhoto")

            assert result.success is True
            assert result.failed_recipients == []
        finally:
            path.unlink()

    @pytest.mark.asyncio
    async def test_uses_spooled_path(self) -> None:
        """Test uses spooled path when provided."""
        mock_client = MagicMock()
        mock_client.send_media = AsyncMock(return_value=(True, None))
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = False

        sender = TelegramMediaSender(mock_client, 30, mock_backoff)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"test")
            spooled_path = Path(f.name)

        try:
            result = await sender.send_media(Path("/source"), "caption", ["user1"], True, "sendPhoto", spooled_path=spooled_path)

            assert result.success is True
            # Verify spooled path was used
            call_args = mock_client.send_media.call_args
            assert call_args[0][1] == spooled_path
        finally:
            spooled_path.unlink()

    @pytest.mark.asyncio
    async def test_raises_on_zero_successes(self) -> None:
        """Test raises RuntimeError on zero successes."""
        mock_client = MagicMock()
        mock_client.send_media = AsyncMock(return_value=(False, "Error"))
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = False

        sender = TelegramMediaSender(mock_client, 30, mock_backoff)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            with pytest.raises(RuntimeError):
                await sender.send_media(path, "caption", ["user1"], True, "sendPhoto")
        finally:
            path.unlink()
