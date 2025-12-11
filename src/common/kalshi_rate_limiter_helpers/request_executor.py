"""Request execution logic"""

import asyncio
import logging
import time
from typing import Any, Dict

import aiohttp

logger = logging.getLogger(__name__)

WORKER_FAILURE_ERRORS = (
    aiohttp.ClientError,
    asyncio.TimeoutError,
    ConnectionError,
    RuntimeError,
    OSError,
)


class RequestExecutor:
    """Executes HTTP requests with error handling"""

    def __init__(self, shutdown_event: asyncio.Event):
        self.shutdown_event = shutdown_event

    async def execute_request(self, request_data: Dict[str, Any]):
        """
        Execute the actual HTTP request and handle response.

        Args:
            request_data: Contains method, path, params, and response callbacks
        """
        request_id = request_data["request_id"]
        queue_wait_time = time.time() - request_data["enqueue_time"]

        if self._should_skip_request(request_id, request_data):
            return

        logger.debug(
            "[KalshiRateLimiter] Executing request %s (queue wait: %.3fs)",
            request_id,
            queue_wait_time,
        )

        try:
            response = await _perform_http_request(request_data)
        except WORKER_FAILURE_ERRORS as exc:
            _handle_request_exception(request_id, exc, request_data)
            return

        _handle_success_callback(request_id, response, request_data)

    def _should_skip_request(self, request_id: str, request_data: Dict[str, Any]) -> bool:
        if not self.shutdown_event.is_set():
            return False
        logger.warning(
            "[KalshiRateLimiter] Skipping request %s - shutdown in progress",
            request_id,
        )
        _invoke_error_callback(request_data, RuntimeError("Rate limiter shutting down"))
        return True


async def _perform_http_request(request_data: Dict[str, Any]):
    http_client = request_data["http_client"]
    return await http_client.make_http_request(
        request_data["method"],
        request_data["path"],
        request_data.get("params"),
    )


def _handle_success_callback(request_id: str, response: Any, request_data: Dict[str, Any]) -> None:
    if "success_callback" in request_data:
        request_data["success_callback"](response)
    logger.debug("[KalshiRateLimiter] Request %s completed successfully", request_id)


def _handle_request_exception(request_id: str, exc: BaseException, request_data: Dict[str, Any]) -> None:
    if _is_shutdown_error(exc):
        logger.info(
            "[KalshiRateLimiter] Request %s cancelled due to shutdown: %s",
            request_id,
            exc,
            exc_info=True,
        )
        return

    logger.error(
        "[KalshiRateLimiter] Request %s failed: %s",
        request_id,
        exc,
        exc_info=True,
    )
    if "error_callback" in request_data:
        request_data["error_callback"](exc)
    else:
        logger.error(
            "[KalshiRateLimiter] Unhandled error in rate-limited request %s: %s",
            request_id,
            exc,
            exc_info=True,
        )


def _is_shutdown_error(exc: BaseException) -> bool:
    error_msg = str(exc).lower()
    return any(
        keyword in error_msg
        for keyword in (
            "invalid state",
            "closed",
            "shutdown",
            "session closed",
            "cannot execute request",
        )
    )


def _invoke_error_callback(request_data: Dict[str, Any], exc: BaseException) -> None:
    callback = request_data.get("error_callback")
    if callable(callback):
        callback(exc)
