"""Tests for alerter_helpers.telegram_polling_request_executor module."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from common.alerter_helpers.telegram_polling_request_executor import (
    TelegramPollingConfig,
    TelegramPollingRequestExecutor,
)


class TestTelegramPollingConfig:
    """Tests for TelegramPollingConfig dataclass."""

    def test_stores_all_fields(self) -> None:
        """Test config stores all fields."""
        timeout = aiohttp.ClientTimeout(total=60)
        config = TelegramPollingConfig(
            url="https://api.telegram.org/bot123/getUpdates",
            params={"offset": 0, "timeout": 30},
            timeout=timeout,
            long_poll_timeout=30,
        )

        assert config.url == "https://api.telegram.org/bot123/getUpdates"
        assert config.params == {"offset": 0, "timeout": 30}
        assert config.timeout == timeout
        assert config.long_poll_timeout == 30

    def test_is_frozen(self) -> None:
        """Test config is frozen (immutable)."""
        timeout = aiohttp.ClientTimeout(total=60)
        config = TelegramPollingConfig(
            url="https://api.telegram.org/bot123/getUpdates",
            params={},
            timeout=timeout,
            long_poll_timeout=30,
        )

        with pytest.raises(AttributeError):
            config.url = "new_url"


class TestTelegramPollingRequestExecutorInit:
    """Tests for TelegramPollingRequestExecutor initialization."""

    def test_stores_dependencies(self) -> None:
        """Test initialization stores dependencies."""
        mock_rate_limit = MagicMock()
        mock_update_processor = MagicMock()
        mock_backoff = MagicMock()
        mock_flush = MagicMock()

        executor = TelegramPollingRequestExecutor(mock_rate_limit, mock_update_processor, mock_backoff, mock_flush)

        assert executor.rate_limit_handler == mock_rate_limit
        assert executor.update_processor == mock_update_processor
        assert executor.backoff_manager == mock_backoff
        assert executor.flush_pending_callback == mock_flush


class TestTelegramPollingRequestExecutorExecutePollingRequest:
    """Tests for execute_polling_request method."""

    @pytest.mark.asyncio
    async def test_handles_rate_limit_response(self) -> None:
        """Test handles 429 rate limit response."""
        mock_rate_limit = MagicMock()
        mock_rate_limit.handle_rate_limit = AsyncMock()
        mock_update_processor = MagicMock()
        mock_backoff = MagicMock()
        mock_flush = AsyncMock()

        executor = TelegramPollingRequestExecutor(mock_rate_limit, mock_update_processor, mock_backoff, mock_flush)

        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        config = TelegramPollingConfig(
            url="https://api.telegram.org/test",
            params={},
            timeout=aiohttp.ClientTimeout(total=60),
            long_poll_timeout=30,
        )

        await executor.execute_polling_request(mock_session, config)

        mock_rate_limit.handle_rate_limit.assert_called_once_with(mock_response)
        mock_flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_non_ok_response(self) -> None:
        """Test handles non-200 response."""
        mock_rate_limit = MagicMock()
        mock_update_processor = MagicMock()
        mock_backoff = MagicMock()
        mock_flush = AsyncMock()

        executor = TelegramPollingRequestExecutor(mock_rate_limit, mock_update_processor, mock_backoff, mock_flush)

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        config = TelegramPollingConfig(
            url="https://api.telegram.org/test",
            params={},
            timeout=aiohttp.ClientTimeout(total=60),
            long_poll_timeout=30,
        )

        await executor.execute_polling_request(mock_session, config)

        mock_flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_processes_successful_response(self) -> None:
        """Test processes successful response."""
        mock_rate_limit = MagicMock()
        mock_update_processor = MagicMock()
        mock_update_processor.process_update = AsyncMock()
        mock_backoff = MagicMock()
        mock_flush = AsyncMock()

        executor = TelegramPollingRequestExecutor(mock_rate_limit, mock_update_processor, mock_backoff, mock_flush)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True, "result": [{"update_id": 1}]})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        config = TelegramPollingConfig(
            url="https://api.telegram.org/test",
            params={},
            timeout=aiohttp.ClientTimeout(total=60),
            long_poll_timeout=30,
        )

        await executor.execute_polling_request(mock_session, config)

        mock_update_processor.process_update.assert_called_once_with({"update_id": 1})
        mock_backoff.clear_backoff.assert_called_once()
        mock_flush.assert_called_once()


class TestTelegramPollingRequestExecutorHandlePollPayload:
    """Tests for _handle_poll_payload method."""

    @pytest.mark.asyncio
    async def test_returns_false_on_api_error(self) -> None:
        """Test returns False on API error."""
        mock_rate_limit = MagicMock()
        mock_update_processor = MagicMock()
        mock_backoff = MagicMock()
        mock_flush = MagicMock()

        executor = TelegramPollingRequestExecutor(mock_rate_limit, mock_update_processor, mock_backoff, mock_flush)

        result = await executor._handle_poll_payload({"ok": False, "error": "Test error"})

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_on_empty_results(self) -> None:
        """Test returns True on empty results."""
        mock_rate_limit = MagicMock()
        mock_update_processor = MagicMock()
        mock_backoff = MagicMock()
        mock_flush = MagicMock()

        executor = TelegramPollingRequestExecutor(mock_rate_limit, mock_update_processor, mock_backoff, mock_flush)

        result = await executor._handle_poll_payload({"ok": True, "result": []})

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_on_non_list_results(self) -> None:
        """Test returns True on non-list results."""
        mock_rate_limit = MagicMock()
        mock_update_processor = MagicMock()
        mock_backoff = MagicMock()
        mock_flush = MagicMock()

        executor = TelegramPollingRequestExecutor(mock_rate_limit, mock_update_processor, mock_backoff, mock_flush)

        result = await executor._handle_poll_payload({"ok": True, "result": "not_a_list"})

        assert result is True

    @pytest.mark.asyncio
    async def test_processes_all_updates(self) -> None:
        """Test processes all updates in result."""
        mock_rate_limit = MagicMock()
        mock_update_processor = MagicMock()
        mock_update_processor.process_update = AsyncMock()
        mock_backoff = MagicMock()
        mock_flush = MagicMock()

        executor = TelegramPollingRequestExecutor(mock_rate_limit, mock_update_processor, mock_backoff, mock_flush)

        result = await executor._handle_poll_payload({"ok": True, "result": [{"update_id": 1}, {"update_id": 2}, {"update_id": 3}]})

        assert result is True
        assert mock_update_processor.process_update.call_count == 3
