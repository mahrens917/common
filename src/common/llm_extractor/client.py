"""Anthropic API client for Claude-based market extraction."""

from __future__ import annotations

import logging

from ._api_key import load_api_key_from_env_file
from ._client_helpers import request_with_retries

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5"
_ANTHROPIC_VERSION = "2023-06-01"
_MAX_TOKENS = 4096


class AnthropicClient:
    """Client for the Anthropic Messages API."""

    INPUT_COST_PER_MTOK = 1.0
    OUTPUT_COST_PER_MTOK = 5.0

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the client with an API key."""
        if api_key:
            self._api_key = api_key
        else:
            loaded_key = load_api_key_from_env_file("ANTHROPIC_API_KEY")
            if not loaded_key:
                raise ValueError("ANTHROPIC_API_KEY not found in ~/.env")
            self._api_key = loaded_key
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        logger.info("Initialized AnthropicClient (model: %s)", _MODEL)

    async def send_message(
        self,
        system_prompt: str,
        user_content: str,
        *,
        json_prefill: str | None = "{",
    ) -> str:
        """Send a message to Claude and return the text response."""
        messages = [{"role": "user", "content": user_content}]
        if json_prefill:
            messages.append({"role": "assistant", "content": json_prefill})

        payload = {
            "model": _MODEL,
            "max_tokens": _MAX_TOKENS,
            "system": system_prompt,
            "messages": messages,
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        response = await request_with_retries(payload, headers, self._accumulate_usage)

        if json_prefill:
            return json_prefill + response
        return response

    def _accumulate_usage(self, data: dict) -> None:
        """Accumulate token usage from API response."""
        usage = data["usage"]
        self._total_input_tokens += usage["input_tokens"]
        self._total_output_tokens += usage["output_tokens"]

    def get_usage(self) -> tuple[int, int]:
        """Return (total_input_tokens, total_output_tokens)."""
        return self._total_input_tokens, self._total_output_tokens

    def get_cost(self) -> float:
        """Calculate total cost in USD based on token usage."""
        input_cost = (self._total_input_tokens / 1_000_000) * self.INPUT_COST_PER_MTOK
        output_cost = (self._total_output_tokens / 1_000_000) * self.OUTPUT_COST_PER_MTOK
        return input_cost + output_cost

    def reset_usage(self) -> None:
        """Reset token counters."""
        self._total_input_tokens = 0
        self._total_output_tokens = 0


__all__ = ["AnthropicClient"]
