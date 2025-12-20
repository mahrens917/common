"""Retry logic for connection manager."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from ..connection_state import ConnectionState

logger = logging.getLogger(__name__)


def _should_continue_retrying(manager: Any) -> bool:
    """Check if retry loop should continue."""
    metrics = manager.metrics_tracker.get_metrics()
    return metrics.consecutive_failures < manager.config.max_consecutive_failures and not manager.shutdown_requested


async def _apply_backoff_if_needed(manager: Any, send_notification: Callable) -> None:
    """Apply backoff delay and send notification if appropriate."""
    metrics = manager.metrics_tracker.get_metrics()
    if metrics.consecutive_failures > 0:
        delay = manager.calculate_backoff_delay()
        if delay > 0:
            await asyncio.sleep(delay)
    if metrics.consecutive_failures == 1:
        await send_notification(is_connected=False, details="Connection lost")


async def _attempt_connection(
    manager: Any,
    establish_connection: Callable,
    transition_state: Callable,
    attempts: int,
) -> tuple[bool, bool]:
    """
    Attempt to establish connection.

    Returns:
        (should_raise, connection_successful)
    """
    try:
        transition_state(ConnectionState.CONNECTING)
        connection_successful = await establish_connection()
        manager.metrics_tracker.metrics.total_reconnection_attempts = attempts
    except (RuntimeError, ConnectionError, ValueError, TypeError) as exc:  # policy_guard: allow-silent-handler
        manager.metrics_tracker.metrics.total_reconnection_attempts = attempts
        transition_state(ConnectionState.FAILED, str(exc))
        metrics = manager.metrics_tracker.get_metrics()
        should_raise = metrics.consecutive_failures >= manager.config.max_consecutive_failures
        return (should_raise, False)
    else:
        return (False, connection_successful)


async def connect_with_retry(
    manager: Any,
    establish_connection: Callable,
    send_notification: Callable,
    transition_state: Callable,
) -> bool:
    """Attempt connection with exponential backoff retry logic."""
    attempts = 0

    while _should_continue_retrying(manager):
        await _apply_backoff_if_needed(manager, send_notification)
        attempts += 1

        should_raise, connection_successful = await _attempt_connection(manager, establish_connection, transition_state, attempts)

        if should_raise:
            raise ConnectionError(f"Failed to connect {manager.service_name} after " f"{manager.config.max_consecutive_failures} attempts")

        if connection_successful:
            manager.metrics_tracker.increment_total_connections()
            transition_state(ConnectionState.READY)
            await send_notification(is_connected=True, details=f"Connection restored after {attempts} attempts")
            return True

        if manager.state != ConnectionState.FAILED:
            transition_state(ConnectionState.FAILED, "Connection establishment failed")

    logger.error(f"Failed to connect {manager.service_name} after " f"{manager.config.max_consecutive_failures} attempts")
    return False
