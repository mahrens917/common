"""WebSocket send/receive operations."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from websockets import WebSocketException


class WebSocketMessageOperations:
    """Handles sending and receiving messages over a WebSocket connection."""

    def __init__(self, service_name: str, connection_provider: Any) -> None:
        self._service_name = service_name
        self._connection_provider = connection_provider
        self._logger = logging.getLogger(f"{__name__}.{service_name}")

    async def send_message(self, message: str) -> bool:
        """Send a message; returns False if the connection is unavailable or an error occurs."""
        ws = self._connection_provider.get_connection()
        if ws is None:
            return False
        with contextlib.suppress(OSError, WebSocketException):
            await ws.send(message)
            return True
        self._logger.debug("Send failed for %s", self._service_name)
        return False

    async def receive_message(self) -> str | None:
        """Receive a message; returns None if the connection is closed or an error occurs."""
        ws = self._connection_provider.get_connection()
        if ws is None:
            return None
        if getattr(ws, "close_code", None) is not None:
            return None
        with contextlib.suppress(OSError, WebSocketException, RuntimeError):
            result = await ws.recv()
            return result.decode() if isinstance(result, bytes) else result
        self._logger.debug("Receive failed for %s", self._service_name)
        return None


__all__ = ["WebSocketMessageOperations"]
