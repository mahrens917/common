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
                AnthropicClient(model="claude-haiku-4-5", max_tokens=4096)

    def test_uses_provided_key(self) -> None:
        """Test that a provided API key is used directly."""
        client = AnthropicClient(model="claude-haiku-4-5", max_tokens=4096, api_key="sk-ant-test")
        assert client._api_key == "sk-ant-test"

    def test_loads_key_from_env(self) -> None:
        """Test that API key is loaded from env file."""
        with patch("common.llm_extractor.client.load_api_key_from_env_file", return_value="sk-ant-env"):
            client = AnthropicClient(model="claude-haiku-4-5", max_tokens=4096)
        assert client._api_key == "sk-ant-env"


class TestAnthropicClientSendMessage:
    """Tests for AnthropicClient.send_message."""

    @pytest.mark.asyncio
    async def test_sends_correct_payload_with_json_mode(self) -> None:
        """Test that the correct payload with assistant prefill is sent in json_mode."""
        client = AnthropicClient(model="claude-haiku-4-5", max_tokens=4096, api_key="sk-ant-test")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        # Response without leading brace (prefill provides it)
        mock_response.json = AsyncMock(
            return_value={"content": [{"type": "text", "text": '"key": "value"}'}], "usage": {"input_tokens": 10, "output_tokens": 5}}
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await client.send_message("system prompt", "user content")

        # Result should have opening brace prepended
        assert result.text == '{"key": "value"}'
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["model"] == "claude-haiku-4-5"
        assert payload["system"] == "system prompt"
        assert payload["messages"][0]["content"] == "user content"
        # Check assistant prefill message
        assert payload["messages"][1]["role"] == "assistant"
        assert payload["messages"][1]["content"] == "{"

        headers = call_kwargs.kwargs["headers"]
        assert headers["x-api-key"] == "sk-ant-test"
        assert headers["anthropic-version"] == "2023-06-01"

    @pytest.mark.asyncio
    async def test_sends_correct_payload_without_prefill(self) -> None:
        """Test that no prefill is added when json_prefill=None."""
        client = AnthropicClient(model="claude-haiku-4-5", max_tokens=4096, api_key="sk-ant-test")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(
            return_value={"content": [{"type": "text", "text": "response text"}], "usage": {"input_tokens": 10, "output_tokens": 5}}
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await client.send_message("system prompt", "user content", json_prefill=None)

        assert result.text == "response text"
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs["json"]
        # Only one message (user), no assistant prefill
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["content"] == "user content"
