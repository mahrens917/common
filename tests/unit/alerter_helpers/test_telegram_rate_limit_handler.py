"""Tests for telegram_rate_limit_handler module."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from common.alerter_helpers.telegram_rate_limit_handler import TelegramRateLimitHandler


class TestTelegramRateLimitHandler:
    """Tests for TelegramRateLimitHandler class."""

    def test_init(self) -> None:
        """Test TelegramRateLimitHandler initialization."""
        handler = TelegramRateLimitHandler()

        assert handler._last_429_time is None
        assert handler._429_count == 0
        assert handler._max_429_retries == 3

    def test_init_custom_max_retries(self) -> None:
        """Test initialization with custom max retries."""
        handler = TelegramRateLimitHandler(max_429_retries=5)

        assert handler._max_429_retries == 5

    def test_is_backoff_active_no_429(self) -> None:
        """Test backoff is inactive when no 429 recorded."""
        handler = TelegramRateLimitHandler()

        result = handler.is_backoff_active()

        assert result is False

    def test_is_backoff_active_during_backoff(self) -> None:
        """Test backoff is active during backoff period."""
        handler = TelegramRateLimitHandler()
        handler._last_429_time = time.time()
        handler._last_429_backoff_seconds = 60

        result = handler.is_backoff_active()

        assert result is True

    def test_is_backoff_active_backoff_expired(self) -> None:
        """Test backoff becomes inactive after expiry."""
        handler = TelegramRateLimitHandler()
        handler._last_429_time = time.time() - 70
        handler._last_429_backoff_seconds = 60

        result = handler.is_backoff_active()

        assert result is False
        assert handler._last_429_time is None
        assert handler._429_count == 0
        assert handler._last_429_backoff_seconds is None

    def test_is_backoff_active_default_exponential_backoff(self) -> None:
        """Test default exponential backoff when no server guidance."""
        handler = TelegramRateLimitHandler()
        handler._last_429_time = time.time()
        handler._429_count = 1
        handler._last_429_backoff_seconds = None

        result = handler.is_backoff_active()

        assert result is True

    @pytest.mark.asyncio
    async def test_handle_rate_limit_with_retry_after(self) -> None:
        """Test handling rate limit with server-provided retry-after."""
        handler = TelegramRateLimitHandler()
        response = MagicMock(spec=aiohttp.ClientResponse)

        with patch.object(
            handler._retry_parser,
            "extract_retry_after_seconds",
            new_callable=AsyncMock,
            return_value=120,
        ):
            await handler.handle_rate_limit(response)

        assert handler._last_429_time is not None
        assert handler._last_429_backoff_seconds == 120
        assert handler._429_count == 0

    @pytest.mark.asyncio
    async def test_handle_rate_limit_without_retry_after(self) -> None:
        """Test handling rate limit without server-provided retry-after."""
        handler = TelegramRateLimitHandler()
        response = MagicMock(spec=aiohttp.ClientResponse)

        with patch.object(
            handler._retry_parser,
            "extract_retry_after_seconds",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await handler.handle_rate_limit(response)

        assert handler._last_429_time is not None
        assert handler._429_count == 1
        assert handler._last_429_backoff_seconds == 60

    @pytest.mark.asyncio
    async def test_handle_rate_limit_exponential_backoff(self) -> None:
        """Test exponential backoff increases with each 429."""
        handler = TelegramRateLimitHandler()
        handler._429_count = 2
        response = MagicMock(spec=aiohttp.ClientResponse)

        with patch.object(
            handler._retry_parser,
            "extract_retry_after_seconds",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await handler.handle_rate_limit(response)

        assert handler._429_count == 3
        assert handler._last_429_backoff_seconds == 240

    @pytest.mark.asyncio
    async def test_handle_rate_limit_max_backoff(self) -> None:
        """Test backoff is capped at 300 seconds."""
        handler = TelegramRateLimitHandler(max_429_retries=5)
        handler._429_count = 4
        response = MagicMock(spec=aiohttp.ClientResponse)

        with patch.object(
            handler._retry_parser,
            "extract_retry_after_seconds",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await handler.handle_rate_limit(response)

        assert handler._last_429_backoff_seconds == 300

    @pytest.mark.asyncio
    async def test_handle_rate_limit_count_capped_at_max_retries(self) -> None:
        """Test 429 count is capped at max retries."""
        handler = TelegramRateLimitHandler(max_429_retries=3)
        handler._429_count = 3
        response = MagicMock(spec=aiohttp.ClientResponse)

        with patch.object(
            handler._retry_parser,
            "extract_retry_after_seconds",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await handler.handle_rate_limit(response)

        assert handler._429_count == 3
