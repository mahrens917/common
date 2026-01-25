"""Tests for llm_extractor client module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.llm_extractor.client import AnthropicClient


class TestAnthropicClientInit:
    """Tests for AnthropicClient initialization."""

    def test_raises_when_no_key_available(self) -> None:
        """Test that ValueError is raised when no API key is found."""
        with patch("common.llm_extractor.client.load_api_key_from_env_file", return_value=None):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                AnthropicClient()

    def test_uses_provided_key(self) -> None:
        """Test that a provided API key is used directly."""
        client = AnthropicClient(api_key="sk-ant-test")
        assert client._api_key == "sk-ant-test"

    def test_loads_key_from_env(self) -> None:
        """Test that API key is loaded from env file."""
        with patch("common.llm_extractor.client.load_api_key_from_env_file", return_value="sk-ant-env"):
            client = AnthropicClient()
        assert client._api_key == "sk-ant-env"


class TestAnthropicClientSendMessage:
    """Tests for AnthropicClient.send_message."""

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self) -> None:
        """Test that the correct payload and headers are sent."""
        client = AnthropicClient(api_key="sk-ant-test")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"content": [{"type": "text", "text": "response text"}]})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await client.send_message("system prompt", "user content")

        assert result == "response text"
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["model"] == "claude-opus-4"
        assert payload["system"] == "system prompt"
        assert payload["messages"][0]["content"] == "user content"

        headers = call_kwargs.kwargs["headers"]
        assert headers["x-api-key"] == "sk-ant-test"
        assert headers["anthropic-version"] == "2023-06-01"

    @pytest.mark.asyncio
    async def test_extracts_text_from_response(self) -> None:
        """Test that text is correctly extracted from Claude response."""
        client = AnthropicClient(api_key="sk-ant-test")
        data = {"content": [{"type": "text", "text": '{"markets": []}'}]}
        result = client._extract_text(data)
        assert result == '{"markets": []}'

    @pytest.mark.asyncio
    async def test_raises_on_missing_text_block(self) -> None:
        """Test that KeyError is raised when no text block exists."""
        client = AnthropicClient(api_key="sk-ant-test")
        data = {"content": [{"type": "image", "source": {}}]}
        with pytest.raises(KeyError, match="No text block"):
            client._extract_text(data)

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit(self) -> None:
        """Test that rate-limited requests are retried."""
        client = AnthropicClient(api_key="sk-ant-test")

        rate_limit_resp = MagicMock()
        rate_limit_resp.status = 429
        rate_limit_resp.headers = {"Retry-After": "0.01"}
        rate_limit_resp.__aenter__ = AsyncMock(return_value=rate_limit_resp)
        rate_limit_resp.__aexit__ = AsyncMock(return_value=False)

        success_resp = MagicMock()
        success_resp.status = 200
        success_resp.raise_for_status = MagicMock()
        success_resp.json = AsyncMock(return_value={"content": [{"type": "text", "text": "ok"}]})
        success_resp.__aenter__ = AsyncMock(return_value=success_resp)
        success_resp.__aexit__ = AsyncMock(return_value=False)

        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return rate_limit_resp
            return success_resp

        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await client.send_message("sys", "user")

        assert result == "ok"
        expected_calls = 1 + 1  # Initial rate-limited call + successful retry
        assert call_count == expected_calls
