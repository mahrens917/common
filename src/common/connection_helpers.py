"""Shared helpers for validating HTTP and WebSocket connections."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from .health.types import HealthCheckResult


async def _interpret_health(check_connection: Callable[[], Awaitable[object]]) -> HealthCheckResult:
    result = await check_connection()
    if isinstance(result, HealthCheckResult):
        return result
    return HealthCheckResult(bool(result))


async def ensure_session_or_raise(
    check_connection: Callable[[], Awaitable[object]],
    *,
    operation: str,
    logger: logging.Logger,
) -> None:
    """
    Ensure an HTTP session or REST transport is ready before proceeding.

    Args:
        check_connection: Awaitable returning either a HealthCheckResult or a boolean.
        operation: Description of the attempted operation.
        logger: Logger used for diagnostics.
    """
    result = await _interpret_health(check_connection)
    if result.healthy:
        return

    error_msg = f"Failed to ensure HTTP session for {operation}"
    if result.error:
        error_msg = f"{error_msg}: {result.error}"
    logger.error(error_msg)
    raise RuntimeError(error_msg)


async def ensure_websocket_or_raise(
    check_connection: Callable[[], Awaitable[object]],
    *,
    operation: str,
    logger: logging.Logger,
) -> None:
    """
    Ensure a WebSocket connection is ready before proceeding.

    Args:
        check_connection: Awaitable returning either a HealthCheckResult or a boolean.
        operation: Description of the attempted operation.
        logger: Logger used for diagnostics.
    """
    result = await _interpret_health(check_connection)
    if result.healthy:
        return

    error_msg = f"Failed to ensure WebSocket connection for {operation}"
    if result.error:
        error_msg = f"{error_msg}: {result.error}"
    logger.error(error_msg)
    raise RuntimeError(error_msg)


__all__ = ["ensure_session_or_raise", "ensure_websocket_or_raise"]
