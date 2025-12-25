"""WebSocket connection lifecycle management."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Optional, Union

import websockets
from websockets import WebSocketException

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection as AsyncClientConnection
    from websockets.client import ClientConnection
    from websockets.sync.client import ClientConnection as SyncClientConnection


class WebSocketConnectionLifecycle:
    """Manages WebSocket connection lifecycle."""

    # Declare dynamically-attached attributes for static type checking
    websocket_connection: Optional[Union[SyncClientConnection, ClientConnection, AsyncClientConnection]]

    def __init__(
        self,
        service_name: str,
        websocket_url: str,
        connection_timeout: float,
        connection_factory: Optional[Callable] = None,
    ):
        self.service_name = service_name
        self.websocket_url = websocket_url
        self.connection_timeout = connection_timeout
        self.connection_factory = connection_factory
        self.websocket_connection = None
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def establish_connection(self) -> bool:
        connected = False
        try:
            self.logger.info("Establishing WebSocket connection to %s", self.websocket_url)

            self.websocket_connection = await _open_websocket(self.connection_factory, self.websocket_url, self.connection_timeout)

            _validate_connection(self.websocket_connection, self.service_name)

            self.logger.info("WebSocket connection established")
            connected = True
        except asyncio.TimeoutError:
            self.logger.exception("WebSocket connection timeout")
            raise TimeoutError(f"WebSocket connection timeout for {self.service_name}")
        except WebSocketException as exc:
            self.logger.exception("WebSocket connection error")
            raise ConnectionError("WebSocket connection failed") from exc
        except (OSError, ValueError) as exc:
            if getattr(exc, "_already_cleaned", None):
                raise
            self.logger.exception("Transport error")
            raise ConnectionError("Transport error") from exc
        except (RuntimeError, AttributeError, TypeError, KeyError):
            self.logger.exception("Unexpected error")
            raise ConnectionError("Unexpected error")
        else:
            return True
        finally:
            if not connected:
                await _cleanup_connection(self)

    async def cleanup_connection(self) -> None:
        if self.websocket_connection:
            try:
                if self.websocket_connection.close_code is None:
                    self.logger.info("Closing WebSocket connection")
                    close_method = getattr(self.websocket_connection, "close")
                    await asyncio.wait_for(close_method(), timeout=5.0)
                else:
                    self.logger.debug("WebSocket already closed (code: %s)", self.websocket_connection.close_code)
            except (
                asyncio.TimeoutError,
                WebSocketException,
                OSError,
                RuntimeError,
            ):  # Transient network/connection failure  # policy_guard: allow-silent-handler
                self.logger.warning("Error closing WebSocket")
            finally:
                self.websocket_connection = None
                self.logger.info("WebSocket connection cleanup completed")

    def is_connected(self) -> bool:
        return self.websocket_connection is not None and self.websocket_connection.close_code is None

    def get_connection(
        self,
    ) -> Optional[Union["SyncClientConnection", "ClientConnection", "AsyncClientConnection"]]:
        return self.websocket_connection


async def _open_websocket(connection_factory, websocket_url: str, timeout: float):
    """Open a websocket via factory or default connector."""
    connector = (
        connection_factory
        if connection_factory
        else lambda: websockets.connect(
            websocket_url,
            ping_interval=None,
            ping_timeout=None,
            close_timeout=10,
            max_size=1024 * 1024,
        )
    )
    return await asyncio.wait_for(connector(), timeout=timeout)


async def _cleanup_connection(lifecycle: "WebSocketConnectionLifecycle") -> None:
    """Module-level indirection so tests can patch cleanup behavior."""
    await lifecycle.cleanup_connection()


def _validate_connection(connection, service_name: str) -> None:
    """Ensure the established connection is usable."""
    if not connection:
        error = ConnectionError(f"WebSocket connection factory failed for {service_name}")
        setattr(error, "_already_cleaned", True)
        raise error

    if connection.close_code is not None:
        error = ConnectionError("WebSocket connection closed during initialization " f"(code: {connection.close_code})")
        setattr(error, "_already_cleaned", True)
        raise error
