"""Anthropic API client for Claude-based market extraction."""

from __future__ import annotations

import json
import logging

import aiohttp

from ._api_key import load_api_key_from_env_file

logger = logging.getLogger(__name__)

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-opus-4"
_API_TIMEOUT_SECONDS = 180
_MAX_RETRIES = 5
_INITIAL_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 60.0
_HTTP_RATE_LIMIT = 429
_HTTP_SERVER_ERROR = 500
_ANTHROPIC_VERSION = "2023-06-01"
_MAX_TOKENS = 4096


class AnthropicClient:
    """Client for the Anthropic Messages API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the client with an API key."""
        if api_key:
            self._api_key = api_key
        else:
            loaded_key = load_api_key_from_env_file("ANTHROPIC_API_KEY")
            if not loaded_key:
                raise ValueError("ANTHROPIC_API_KEY not found in ~/.env")
            self._api_key = loaded_key
        logger.info("Initialized AnthropicClient (model: %s)", _MODEL)

    async def send_message(self, system_prompt: str, user_content: str) -> str:
        """Send a message to Claude and return the text response.

        Args:
            system_prompt: The system prompt.
            user_content: The user message content.

        Returns:
            The text content from Claude's response.

        Raises:
            RuntimeError: If the API call fails after all retries.
        """
        payload = {
            "model": _MODEL,
            "max_tokens": _MAX_TOKENS,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        return await self._request_with_retries(payload, headers)

    async def _request_with_retries(self, payload: dict, headers: dict) -> str:
        """Execute the API request with exponential backoff retry logic."""
        import asyncio

        backoff = _INITIAL_BACKOFF_SECONDS
        timeout = aiohttp.ClientTimeout(total=_API_TIMEOUT_SECONDS)

        for attempt in range(_MAX_RETRIES):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(_ANTHROPIC_API_URL, json=payload, headers=headers) as resp:
                        if resp.status == _HTTP_RATE_LIMIT:
                            wait = self._get_retry_wait(resp, backoff, attempt)
                            await asyncio.sleep(wait)
                            backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
                            continue

                        if resp.status >= _HTTP_SERVER_ERROR:
                            logger.warning("Server error (%d), retry %d/%d", resp.status, attempt + 1, _MAX_RETRIES)
                            await asyncio.sleep(backoff)
                            backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
                            continue

                        resp.raise_for_status()
                        data = await resp.json()
                        return self._extract_text(data)

            except aiohttp.ClientError as exc:
                logger.warning("API call failed (attempt %d/%d): %s", attempt + 1, _MAX_RETRIES, exc)
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
                    continue
                raise RuntimeError(f"Anthropic API call failed after {_MAX_RETRIES} retries") from exc

        raise RuntimeError(f"Anthropic API call failed after {_MAX_RETRIES} retries")

    def _get_retry_wait(self, resp: aiohttp.ClientResponse, backoff: float, attempt: int) -> float:
        """Determine wait time from rate limit response."""
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            wait = float(retry_after)
        else:
            wait = backoff
        logger.warning("Rate limited (429), waiting %.1fs before retry %d/%d", wait, attempt + 1, _MAX_RETRIES)
        return wait

    def _extract_text(self, data: dict) -> str:
        """Extract text content from Claude API response."""
        content = data["content"]
        for block in content:
            if block["type"] == "text":
                return block["text"]
        raise KeyError("No text block found in Claude response")


__all__ = ["AnthropicClient"]
