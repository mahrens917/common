"""Thread-based WebSocket keepalive that isolates ping timing from asyncio event loop saturation.

The keepalive thread uses OS-level timing (threading.Event.wait) and
concurrent.futures for pong timeouts, so a saturated event loop cannot
cause false disconnect detection.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

_THREAD_TIMEOUT_BUFFER_SECONDS = 2.0
_MAX_MISSED_PONGS = 3
_POLL_INTERVAL_SECONDS = 1.0


class KeepaliveError(Exception):
    """Raised when keepalive detects connection loss."""


def _handle_ping_result(
    future: concurrent.futures.Future,
    missed_pongs: int,
    max_missed: int,
    stop_event: threading.Event,
    thread_name: str,
) -> int:
    """Inspect a completed ping future and return the updated missed_pongs count.

    Sets stop_event on fatal errors (max missed or connection loss).
    """
    if future.cancelled():
        stop_event.set()
        return missed_pongs

    exc = future.exception()
    if exc is None:
        _none_guard_value = 0
        return _none_guard_value

    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        missed_pongs += 1
        logger.warning("%s keepalive pong missed (%d/%d)", thread_name, missed_pongs, max_missed)
        if missed_pongs >= max_missed:
            logger.warning("%s max missed pongs reached (%d) - connection lost", thread_name, max_missed)
            stop_event.set()
        return missed_pongs

    logger.warning("%s keepalive error: %s", thread_name, exc)
    stop_event.set()
    return missed_pongs


def _keepalive_thread(
    ping_fn: Callable[[], Coroutine[Any, Any, None]],
    loop: asyncio.AbstractEventLoop,
    interval: float,
    ping_timeout: float,
    max_missed: int,
    stop_event: threading.Event,
    thread_name: str,
) -> None:
    """Dedicated thread for keepalive. Exits on max missed pongs or connection error."""
    missed_pongs = 0
    full_timeout = ping_timeout + _THREAD_TIMEOUT_BUFFER_SECONDS
    logger.info("%s keepalive thread started (interval=%.0fs, timeout=%.0fs)", thread_name, interval, ping_timeout)

    while not stop_event.wait(timeout=interval):
        future = asyncio.run_coroutine_threadsafe(ping_fn(), loop)
        completed, _ = concurrent.futures.wait({future}, timeout=full_timeout)

        if not completed:
            future.cancel()
            missed_pongs += 1
            logger.warning("%s keepalive pong missed (%d/%d)", thread_name, missed_pongs, max_missed)
            if missed_pongs >= max_missed:
                logger.warning("%s max missed pongs reached (%d) - connection lost", thread_name, max_missed)
                stop_event.set()
            continue

        missed_pongs = _handle_ping_result(future, missed_pongs, max_missed, stop_event, thread_name)


async def run_threaded_keepalive(
    ping_fn: Callable[[], Coroutine[Any, Any, None]],
    interval: float,
    ping_timeout: float,
    max_missed: int = _MAX_MISSED_PONGS,
    is_shutdown: Callable[[], bool] = lambda: False,
    thread_name: str = "ws",
) -> None:
    """Run keepalive on a dedicated thread.

    Raises KeepaliveError on connection loss. Returns normally on shutdown.

    Args:
        ping_fn: Coroutine factory that sends a ping and awaits the pong.
                 Should raise on timeout or connection error.
        interval: Seconds between pings.
        ping_timeout: Seconds to wait for pong response.
        max_missed: Consecutive missed pongs before declaring failure.
        is_shutdown: Callable returning True when shutdown is requested.
        thread_name: Service name for log messages and thread naming.
    """
    loop = asyncio.get_running_loop()
    stop_event = threading.Event()

    thread = threading.Thread(
        target=_keepalive_thread,
        args=(ping_fn, loop, interval, ping_timeout, max_missed, stop_event, thread_name),
        name=f"{thread_name}_keepalive",
        daemon=True,
    )
    thread.start()

    try:
        while not is_shutdown() and thread.is_alive():
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    finally:
        stop_event.set()
        thread.join(timeout=ping_timeout + _THREAD_TIMEOUT_BUFFER_SECONDS + 1)

    if not is_shutdown():
        raise KeepaliveError(f"{thread_name} keepalive detected connection loss")
