"""HTTP request helpers for Anthropic API client."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

logger = logging.getLogger(__name__)

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_API_TIMEOUT_SECONDS = 180
_MAX_RETRIES = 5
_INITIAL_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 60.0
_HTTP_CLIENT_ERROR = 400
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

    Collects ALL text blocks and joins with newline. Web search responses
    interleave text with tool_use/web_search_tool_result blocks.

    Args:
        data: The response data dict.

    Returns:
        The joined text content.

    Raises:
        KeyError: If no text block found.
    """
    parts = [block["text"] for block in data["content"] if block["type"] == "text"]
    if not parts:
        raise KeyError("No text block found in Claude response")
    return "\n".join(parts)


async def request_with_retries(
    payload: dict,
    headers: dict,
) -> dict:
    """Execute the API request with exponential backoff retry logic.

    Args:
        payload: The request payload.
        headers: The request headers.

    Returns:
        The full response JSON dict.

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

                    if resp.status >= _HTTP_CLIENT_ERROR:
                        error_body = await resp.text()
                        raise RuntimeError(f"Anthropic API error ({resp.status}): {error_body}")

                    return await resp.json()

        except aiohttp.ClientError as exc:
            logger.warning("API call failed (attempt %d/%d): %s", attempt + 1, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
                continue
            raise RuntimeError(f"Anthropic API call failed after {_MAX_RETRIES} retries") from exc

    raise RuntimeError(f"Anthropic API call failed after {_MAX_RETRIES} retries")


__all__ = ["request_with_retries", "extract_text", "get_retry_wait"]
