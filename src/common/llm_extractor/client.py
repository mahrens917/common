"""Anthropic API client for Claude-based market extraction."""

from __future__ import annotations

import logging

from ._api_key import load_api_key_from_env_file
from ._client_helpers import request_with_retries

logger = logging.getLogger(__name__)

_ANTHROPIC_VERSION = "2023-06-01"

_MODEL_COSTS: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-opus-4": (15.0, 75.0),
}


class AnthropicClient:
    """Client for the Anthropic Messages API."""

    def __init__(self, *, model: str, max_tokens: int, api_key: str | None = None) -> None:
        """Initialize the client with model, max_tokens, and an API key."""
        if api_key:
            self._api_key = api_key
        else:
            loaded_key = load_api_key_from_env_file("ANTHROPIC_API_KEY")
            if not loaded_key:
                raise ValueError("ANTHROPIC_API_KEY not found in ~/.env")
            self._api_key = loaded_key
        self._model = model
        self._max_tokens = max_tokens
        costs = _MODEL_COSTS[model]
        self._input_cost_per_mtok = costs[0]
        self._output_cost_per_mtok = costs[1]
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        logger.info("Initialized AnthropicClient (model: %s)", self._model)

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
            "model": self._model,
            "max_tokens": self._max_tokens,
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
        input_cost = (self._total_input_tokens / 1_000_000) * self._input_cost_per_mtok
        output_cost = (self._total_output_tokens / 1_000_000) * self._output_cost_per_mtok
        return input_cost + output_cost

    def reset_usage(self) -> None:
        """Reset token counters."""
        self._total_input_tokens = 0
        self._total_output_tokens = 0


__all__ = ["AnthropicClient"]
