"""Tests for llm_extractor client helpers module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from common.llm_extractor._client_helpers import (
    _HTTP_RATE_LIMIT,
    _HTTP_SERVER_ERROR,
    _MAX_RETRIES,
    extract_text,
    get_retry_wait,
    request_with_retries,
)


class TestGetRetryWait:
    """Tests for get_retry_wait."""

    def test_uses_retry_after_header(self) -> None:
        """Test that Retry-After header is used when present."""
        mock_resp = MagicMock()
        mock_resp.headers = {"Retry-After": "5"}
        wait = get_retry_wait(mock_resp, 2.0, 0)
        assert wait == 5.0

    def test_uses_backoff_when_no_header(self) -> None:
        """Test that backoff value is used when no Retry-After header."""
        mock_resp = MagicMock()
        mock_resp.headers = {}
        wait = get_retry_wait(mock_resp, 3.0, 0)
        assert wait == 3.0


class TestExtractText:
    """Tests for extract_text."""

    def test_extracts_text_block(self) -> None:
        """Test extracting text from response."""
        data = {"content": [{"type": "text", "text": "Hello world"}]}
        assert extract_text(data) == "Hello world"

    def test_raises_on_missing_text(self) -> None:
        """Test that KeyError is raised when no text block."""
        data = {"content": [{"type": "image", "data": "..."}]}
        with pytest.raises(KeyError, match="No text block"):
            extract_text(data)


class TestRequestWithRetries:
    """Tests for request_with_retries."""

    @pytest.mark.asyncio
    async def test_successful_request(self) -> None:
        """Test successful request returns text."""
        accumulator = MagicMock()

        with patch("common.llm_extractor._client_helpers.aiohttp.ClientSession") as mock_session_cls:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json = AsyncMock(return_value={"content": [{"type": "text", "text": "OK"}], "usage": {}})
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock()

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_resp)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_session_cls.return_value = mock_session

            result = await request_with_retries({"model": "test"}, {"x-api-key": "key"}, accumulator)

        assert result == "OK"
        accumulator.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit(self) -> None:
        """Test that request retries on 429 status."""
        accumulator = MagicMock()
        call_count = 0

        with patch("common.llm_extractor._client_helpers.aiohttp.ClientSession") as mock_session_cls:
            with patch("common.llm_extractor._client_helpers.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

                def make_response():
                    nonlocal call_count
                    call_count += 1
                    mock_resp = MagicMock()
                    if call_count == 1:
                        mock_resp.status = _HTTP_RATE_LIMIT
                        mock_resp.headers = {"Retry-After": "0.01"}
                    else:
                        mock_resp.status = 200
                        mock_resp.raise_for_status = MagicMock()
                        mock_resp.json = AsyncMock(return_value={"content": [{"type": "text", "text": "OK"}], "usage": {}})
                    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
                    mock_resp.__aexit__ = AsyncMock()
                    return mock_resp

                mock_session = MagicMock()
                mock_session.post = MagicMock(side_effect=lambda *a, **kw: make_response())
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock()
                mock_session_cls.return_value = mock_session

                result = await request_with_retries({"model": "test"}, {"x-api-key": "key"}, accumulator)

        assert result == "OK"
        expected_calls = 1 + 1  # rate-limited + success
        assert call_count == expected_calls
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_server_error(self) -> None:
        """Test that request retries on 500+ status."""
        accumulator = MagicMock()
        call_count = 0

        with patch("common.llm_extractor._client_helpers.aiohttp.ClientSession") as mock_session_cls:
            with patch("common.llm_extractor._client_helpers.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

                def make_response():
                    nonlocal call_count
                    call_count += 1
                    mock_resp = MagicMock()
                    if call_count == 1:
                        mock_resp.status = _HTTP_SERVER_ERROR
                        mock_resp.headers = {}
                    else:
                        mock_resp.status = 200
                        mock_resp.raise_for_status = MagicMock()
                        mock_resp.json = AsyncMock(return_value={"content": [{"type": "text", "text": "OK"}], "usage": {}})
                    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
                    mock_resp.__aexit__ = AsyncMock()
                    return mock_resp

                mock_session = MagicMock()
                mock_session.post = MagicMock(side_effect=lambda *a, **kw: make_response())
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock()
                mock_session_cls.return_value = mock_session

                result = await request_with_retries({"model": "test"}, {"x-api-key": "key"}, accumulator)

        assert result == "OK"
        expected_calls = 1 + 1  # server-error + success
        assert call_count == expected_calls
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_after_max_retries_on_client_error(self) -> None:
        """Test that RuntimeError is raised after max retries on client error."""
        accumulator = MagicMock()

        with patch("common.llm_extractor._client_helpers.aiohttp.ClientSession") as mock_session_cls:
            with patch("common.llm_extractor._client_helpers.asyncio.sleep", new_callable=AsyncMock):
                mock_session = MagicMock()
                mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock()
                mock_session_cls.return_value = mock_session

                with pytest.raises(RuntimeError, match=f"after {_MAX_RETRIES} retries"):
                    await request_with_retries({"model": "test"}, {"x-api-key": "key"}, accumulator)
