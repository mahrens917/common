"""Tests for alerting.telegram_client module."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from common.alerting.telegram_client import TelegramClient


class TestTelegramClientInit:
    """Tests for TelegramClient initialization."""

    def test_init_sets_base_url(self) -> None:
        """Test initialization sets base URL with token."""
        client = TelegramClient("test_token", timeout_seconds=30.0)

        assert client.base_url == "https://api.telegram.org/bottest_token"

    def test_init_sets_timeout(self) -> None:
        """Test initialization sets timeout."""
        client = TelegramClient("test_token", timeout_seconds=60.0)

        assert client.timeout.total == 60.0


class TestSendMessage:
    """Tests for send_message method."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Test successful message send."""
        client = TelegramClient("test_token", timeout_seconds=30.0)
        mock_response = MagicMock()
        mock_response.status = 200

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(
                return_value=MagicMock(
                    __aenter__=AsyncMock(return_value=mock_response),
                    __aexit__=AsyncMock(return_value=None),
                )
            )
            mock_session_cls.return_value = mock_session

            success, error = await client.send_message("123", "Hello")

        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_failure(self) -> None:
        """Test failed message send."""
        client = TelegramClient("test_token", timeout_seconds=30.0)
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(
                return_value=MagicMock(
                    __aenter__=AsyncMock(return_value=mock_response),
                    __aexit__=AsyncMock(return_value=None),
                )
            )
            mock_session_cls.return_value = mock_session

            success, error = await client.send_message("123", "Hello")

        assert success is False
        assert error == "Bad Request"


class TestSendMedia:
    """Tests for send_media method."""

    @pytest.mark.asyncio
    async def test_missing_payload(self) -> None:
        """Test returns error when payload missing."""
        client = TelegramClient("test_token", timeout_seconds=30.0)
        missing_path = Path("/nonexistent/file.png")

        success, error = await client.send_media(
            chat_id="123",
            payload_path=missing_path,
            caption="Test",
            is_photo=True,
            method="sendPhoto",
        )

        assert success is False
        assert "Payload missing" in error

    @pytest.mark.asyncio
    async def test_success_photo(self) -> None:
        """Test successful photo send."""
        client = TelegramClient("test_token", timeout_seconds=30.0)
        mock_response = MagicMock()
        mock_response.status = 200

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = Path(f.name)

        try:
            with patch("aiohttp.ClientSession") as mock_session_cls:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.post = MagicMock(
                    return_value=MagicMock(
                        __aenter__=AsyncMock(return_value=mock_response),
                        __aexit__=AsyncMock(return_value=None),
                    )
                )
                mock_session_cls.return_value = mock_session

                success, error = await client.send_media(
                    chat_id="123",
                    payload_path=temp_path,
                    caption="Test photo",
                    is_photo=True,
                    method="sendPhoto",
                )

            assert success is True
            assert error is None
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_success_document(self) -> None:
        """Test successful document send."""
        client = TelegramClient("test_token", timeout_seconds=30.0)
        mock_response = MagicMock()
        mock_response.status = 200

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake document data")
            temp_path = Path(f.name)

        try:
            with patch("aiohttp.ClientSession") as mock_session_cls:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.post = MagicMock(
                    return_value=MagicMock(
                        __aenter__=AsyncMock(return_value=mock_response),
                        __aexit__=AsyncMock(return_value=None),
                    )
                )
                mock_session_cls.return_value = mock_session

                success, error = await client.send_media(
                    chat_id="123",
                    payload_path=temp_path,
                    caption="Test document",
                    is_photo=False,
                    method="sendDocument",
                )

            assert success is True
            assert error is None
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_failure(self) -> None:
        """Test failed media send."""
        client = TelegramClient("test_token", timeout_seconds=30.0)
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = Path(f.name)

        try:
            with patch("aiohttp.ClientSession") as mock_session_cls:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.post = MagicMock(
                    return_value=MagicMock(
                        __aenter__=AsyncMock(return_value=mock_response),
                        __aexit__=AsyncMock(return_value=None),
                    )
                )
                mock_session_cls.return_value = mock_session

                success, error = await client.send_media(
                    chat_id="123",
                    payload_path=temp_path,
                    caption="Test",
                    is_photo=True,
                    method="sendPhoto",
                )

            assert success is False
            assert error == "Bad Request"
        finally:
            temp_path.unlink()


class TestGetUpdates:
    """Tests for get_updates method."""

    @pytest.mark.asyncio
    async def test_returns_json(self) -> None:
        """Test returns JSON response."""
        client = TelegramClient("test_token", timeout_seconds=30.0)
        expected_data = {"ok": True, "result": []}
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=expected_data)

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = MagicMock(
                return_value=MagicMock(
                    __aenter__=AsyncMock(return_value=mock_response),
                    __aexit__=AsyncMock(return_value=None),
                )
            )
            mock_session_cls.return_value = mock_session

            result = await client.get_updates({"offset": 0})

        assert result == expected_data
