"""Request execution logic for Kalshi API."""

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

from .client_helpers.errors import KalshiClientError

logger = logging.getLogger(__name__)

HTTP_TOO_MANY_REQUESTS = 429


class RequestExecutor:
    """Execute HTTP requests with retries and error handling."""

    def __init__(self, session_manager, auth_helper, max_retries, backoff_base, backoff_max):
        self._session_manager = session_manager
        self._auth_helper = auth_helper
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max

    async def execute_request(
        self, method_upper: str, url: str, request_kwargs: Dict[str, Any], path: str, operation_name: str
    ) -> Dict[str, Any]:
        """Execute HTTP request with authentication headers and error handling."""
        await self._session_manager.initialize()
        session = self._session_manager.get_session()
        if request_kwargs.get("headers") is None:
            request_kwargs["headers"] = self._auth_helper.create_auth_headers(method_upper, path)
        return await self._retry_request(session, method_upper, url, request_kwargs, path, operation_name)

    async def _retry_request(
        self, session: aiohttp.ClientSession, method_upper: str, url: str, request_kwargs: Dict[str, Any], path: str, op: str
    ) -> Dict[str, Any]:
        max_attempts = max(1, self._max_retries)
        last_exception: Optional[BaseException] = None
        for attempt in range(1, max_attempts + 1):
            try:
                async with session.request(method_upper, url, **request_kwargs) as response:
                    if response.status == HTTP_TOO_MANY_REQUESTS:
                        if attempt < max_attempts:
                            delay = self._compute_retry_delay(attempt)
                            logger.debug("Kalshi rate limited %s (%d/%d); retrying in %.1fs", op, attempt, max_attempts, delay)
                            await asyncio.sleep(delay)
                            continue
                        raise KalshiClientError(f"Kalshi rate limit exceeded for {op} after {max_attempts} attempts")
                    return await self._parse_json_response(response, await response.text(), path=path)
            except aiohttp.ClientError as exc:
                last_exception = exc
                if attempt < max_attempts:
                    delay = self._compute_retry_delay(attempt)
                    logger.warning("Kalshi request %s failed (%d/%d): %s; retrying in %.1fs", op, attempt, max_attempts, exc, delay)
                    await asyncio.sleep(delay)
                else:
                    logger.exception("Kalshi request %s failed after %d attempts", op, max_attempts)
                    raise
        if last_exception is not None:
            raise KalshiClientError(f"Kalshi request failed for {op}: {last_exception}") from last_exception
        raise KalshiClientError(f"Kalshi request failed for {op} without exception")

    def _compute_retry_delay(self, attempt: int) -> float:
        if attempt < 1:
            raise TypeError("Retry attempt must be at least 1")
        base_backoff = max(0.5, float(self._backoff_base))
        max_backoff = max(base_backoff, float(self._backoff_max))
        return min(base_backoff * (2 ** (attempt - 1)), max_backoff)

    async def _parse_json_response(self, response: aiohttp.ClientResponse, text: str, *, path: str) -> Dict[str, Any]:
        try:
            payload = await response.json()
        except aiohttp.ContentTypeError as exc:
            raise KalshiClientError(f"Kalshi response was not JSON for {path}: {text}") from exc
        if response.status not in {200, 201, 202}:
            raise KalshiClientError(f"Kalshi request {path} returned {response.status}: {payload}")
        if not isinstance(payload, dict):
            raise KalshiClientError(f"Kalshi response for {path} was not a JSON object")
        return payload
