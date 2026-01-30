"""HTTP request helpers for Anthropic API client."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

import aiohttp

logger = logging.getLogger(__name__)

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_API_TIMEOUT_SECONDS = 180
_MAX_RETRIES = 5
_INITIAL_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 60.0
_HTTP_RATE_LIMIT = 429
_HTTP_SERVER_ERROR = 500


def get_retry_wait(resp: aiohttp.ClientResponse, backoff: float, attempt: int) -> float:
    """Determine wait time from rate limit response.

    Args:
        resp: The HTTP response.
        backoff: Current backoff value in seconds.
        attempt: Current attempt number.

    Returns:
        Wait time in seconds.
    """
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        wait = float(retry_after)
    else:
        wait = backoff
    logger.warning("Rate limited (429), waiting %.1fs before retry %d/%d", wait, attempt + 1, _MAX_RETRIES)
    return wait


def extract_text(data: dict) -> str:
    """Extract text content from Claude API response.

    Args:
        data: The response data dict.

    Returns:
        The text content.

    Raises:
        KeyError: If no text block found.
    """
    content = data["content"]
    for block in content:
        if block["type"] == "text":
            return block["text"]
    raise KeyError("No text block found in Claude response")


async def request_with_retries(
    payload: dict,
    headers: dict,
    accumulate_usage_fn: Callable[[dict], None],
) -> str:
    """Execute the API request with exponential backoff retry logic.

    Args:
        payload: The request payload.
        headers: The request headers.
        accumulate_usage_fn: Function to accumulate token usage.

    Returns:
        The text response.

    Raises:
        RuntimeError: If all retries are exhausted.
    """
    backoff = _INITIAL_BACKOFF_SECONDS
    timeout = aiohttp.ClientTimeout(total=_API_TIMEOUT_SECONDS)

    for attempt in range(_MAX_RETRIES):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(_ANTHROPIC_API_URL, json=payload, headers=headers) as resp:
                    if resp.status == _HTTP_RATE_LIMIT:
                        wait = get_retry_wait(resp, backoff, attempt)
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
                    accumulate_usage_fn(data)
                    return extract_text(data)

        except aiohttp.ClientError as exc:
            logger.warning("API call failed (attempt %d/%d): %s", attempt + 1, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
                continue
            raise RuntimeError(f"Anthropic API call failed after {_MAX_RETRIES} retries") from exc

    raise RuntimeError(f"Anthropic API call failed after {_MAX_RETRIES} retries")


__all__ = ["request_with_retries", "extract_text", "get_retry_wait"]
