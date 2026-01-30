"""Request execution logic for Kalshi API."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict

import aiohttp

from .client_helpers.errors import KalshiClientError

logger = logging.getLogger(__name__)

HTTP_TOO_MANY_REQUESTS = 429
HTTP_RETRYABLE_SERVER_ERRORS = (500, 502, 503, 504)


@dataclass
class _AttemptContext:
    """Context for a single request attempt."""

    path: str
    op: str
    attempt: int
    max_attempts: int


@dataclass
class _RetryResult:
    """Result indicating a retry is needed."""

    delay: float


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
        for attempt in range(1, max_attempts + 1):
            ctx = _AttemptContext(path=path, op=op, attempt=attempt, max_attempts=max_attempts)
            result = await self._execute_single_attempt(session, method_upper, url, request_kwargs, ctx)
            if isinstance(result, _RetryResult):
                await asyncio.sleep(result.delay)
                continue
            return result
        raise AssertionError("Unreachable: retry loop exited without returning or raising")

    async def _execute_single_attempt(
        self, session: aiohttp.ClientSession, method_upper: str, url: str, request_kwargs: Dict[str, Any], ctx: _AttemptContext
    ) -> Dict[str, Any] | _RetryResult:
        try:
            async with session.request(method_upper, url, **request_kwargs) as response:
                return await self._handle_response(response, ctx)
        except (aiohttp.ClientError, TimeoutError) as exc:
            result = self._handle_client_error(exc, ctx)
            if isinstance(result, _RetryResult):
                return result
            raise result from exc

    async def _handle_response(self, response: aiohttp.ClientResponse, ctx: _AttemptContext) -> Dict[str, Any] | _RetryResult:
        if response.status == HTTP_TOO_MANY_REQUESTS:
            return self._handle_rate_limit(ctx)
        if response.status in HTTP_RETRYABLE_SERVER_ERRORS:
            return self._handle_server_error(response.status, ctx)
        return await self._parse_json_response(response, await response.text(), path=ctx.path)

    def _handle_rate_limit(self, ctx: _AttemptContext) -> _RetryResult:
        if ctx.attempt >= ctx.max_attempts:
            raise KalshiClientError(f"Kalshi rate limit exceeded for {ctx.op} after {ctx.max_attempts} attempts")
        delay = self._compute_retry_delay(ctx.attempt)
        logger.debug("Kalshi rate limited %s (%d/%d); retrying in %.1fs", ctx.op, ctx.attempt, ctx.max_attempts, delay)
        return _RetryResult(delay)

    def _handle_server_error(self, status: int, ctx: _AttemptContext) -> _RetryResult:
        if ctx.attempt >= ctx.max_attempts:
            raise KalshiClientError(f"Kalshi server error {status} for {ctx.op} after {ctx.max_attempts} attempts")
        delay = self._compute_retry_delay(ctx.attempt)
        logger.warning("Kalshi server error %d for %s (%d/%d); retrying in %.1fs", status, ctx.op, ctx.attempt, ctx.max_attempts, delay)
        return _RetryResult(delay)

    def _handle_client_error(self, exc: Exception, ctx: _AttemptContext) -> KalshiClientError | _RetryResult:
        if ctx.attempt >= ctx.max_attempts:
            logger.exception("Kalshi request %s failed after %d attempts", ctx.op, ctx.max_attempts)
            return KalshiClientError(f"Kalshi request failed for {ctx.op}: {exc}")
        delay = self._compute_retry_delay(ctx.attempt)
        logger.warning("Kalshi request %s failed (%d/%d): %s; retrying in %.1fs", ctx.op, ctx.attempt, ctx.max_attempts, exc, delay)
        return _RetryResult(delay)

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
