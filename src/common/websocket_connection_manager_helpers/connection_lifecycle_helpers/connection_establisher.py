"""Establish WebSocket connections with proper error handling."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Tuple

import websockets
from websockets import WebSocketException

logger = logging.getLogger(__name__)


class ConnectionAlreadyCleanedError(ConnectionError):
    """Signal that connection cleanup has already occurred."""


@dataclass(frozen=True)
class _ErrorMapping:
    exc_types: Tuple[type, ...]
    log_message: str
    exception_factory: Callable[[str], Exception]


_ERROR_MAPPINGS = (
    _ErrorMapping(
        exc_types=(asyncio.TimeoutError,),
        log_message="WebSocket connection timeout",
        exception_factory=lambda service: TimeoutError(f"WebSocket connection timeout for {service}"),
    ),
    _ErrorMapping(
        exc_types=(WebSocketException,),
        log_message="WebSocket connection error",
        exception_factory=lambda service: ConnectionError("WebSocket connection failed"),
    ),
    _ErrorMapping(
        exc_types=(OSError, ValueError),
        log_message="Transport error",
        exception_factory=lambda service: ConnectionError("Transport error"),
    ),
    _ErrorMapping(
        exc_types=(RuntimeError, AttributeError, TypeError, KeyError),
        log_message="Unexpected error",
        exception_factory=lambda service: ConnectionError("Unexpected error"),
    ),
    _ErrorMapping(
        exc_types=(Exception,),
        log_message="Unexpected error",
        exception_factory=lambda service: ConnectionError("Unexpected error"),
    ),
)


async def connect_with_factory(connection_factory: Callable, timeout: float, service_name: str) -> Any:
    """
    Connect using provided factory with timeout.

    Args:
        connection_factory: Async callable that returns WebSocket connection
        timeout: Connection timeout in seconds
        service_name: Name of service for logging

    Returns:
        WebSocket connection object

    Raises:
        ConnectionError: If factory returns None or connection is closed
        TimeoutError: If connection times out
    """
    try:
        websocket_connection = await asyncio.wait_for(connection_factory(), timeout=timeout)
    except (
        asyncio.TimeoutError,
        WebSocketException,
        OSError,
        ValueError,
        RuntimeError,
        AttributeError,
        TypeError,
        KeyError,
        ConnectionError,
    ) as exc:
        handled_exc = handle_connection_error(exc, service_name, logger)
        if handled_exc is exc:
            raise
        raise handled_exc from exc

    if not websocket_connection:
        raise ConnectionAlreadyCleanedError(f"WebSocket connection factory failed for {service_name}")

    if websocket_connection.close_code is not None:
        raise ConnectionAlreadyCleanedError(f"WebSocket connection closed during initialization (code: {websocket_connection.close_code})")

    return websocket_connection


async def connect_with_defaults(url: str, timeout: float) -> Any:
    """
    Connect to WebSocket URL with default settings.

    Args:
        url: WebSocket URL
        timeout: Connection timeout in seconds

    Returns:
        WebSocket connection object
    """
    return await asyncio.wait_for(
        websockets.connect(
            url,
            ping_interval=None,
            ping_timeout=None,
            close_timeout=10,
            max_size=1024 * 1024,
        ),
        timeout=timeout,
    )


def handle_connection_error(exc: Exception, service_name: str, logger_instance: logging.Logger) -> Exception:
    """
    Handle connection errors and convert to appropriate exception type.

    Args:
        exc: Original exception
        service_name: Name of service
        logger_instance: Logger instance

    Returns:
        Appropriate exception to raise
    """
    if getattr(exc, "_already_cleaned", None):
        return exc

    if isinstance(exc, ConnectionAlreadyCleanedError):
        return exc

    for mapping in _ERROR_MAPPINGS:
        if isinstance(exc, mapping.exc_types):
            logger_instance.error(mapping.log_message)
            return mapping.exception_factory(service_name)

    return exc
