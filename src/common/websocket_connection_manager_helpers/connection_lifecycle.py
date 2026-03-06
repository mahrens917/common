"""WebSocket connection lifecycle management."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable


def _validate_connection(conn: Any, service_name: str) -> None:
    """Raise ConnectionError if the connection is None or already closed."""
    if conn is None:
        err = ConnectionError(f"WebSocket connection is None for {service_name}")
        setattr(err, "_already_cleaned", True)
        raise err
    if getattr(conn, "close_code", None) is not None:
        err = ConnectionError(f"WebSocket connection is closed for {service_name} (code={conn.close_code})")
        setattr(err, "_already_cleaned", True)
        raise err


class WebSocketConnectionLifecycle:
    """Manages the establish/cleanup lifecycle for a WebSocket connection."""

    def __init__(
        self,
        service_name: str,
        url: str,
        *,
        connection_timeout: float,
        connection_factory: Callable[[], Any],
    ) -> None:
        self.service_name = service_name
        self.url = url
        self.connection_timeout = connection_timeout
        self.connection_factory = connection_factory
        self._connection: Any = None
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def establish_connection(self) -> None:
        """Establish the WebSocket connection, raising ConnectionError on failure."""
        try:
            conn = await asyncio.wait_for(self.connection_factory(), timeout=self.connection_timeout)
            _validate_connection(conn, self.service_name)
            self._connection = conn
        except ConnectionError:
            raise
        except (OSError, asyncio.TimeoutError) as exc:
            await self.cleanup_connection()
            raise ConnectionError(f"Transport error for {self.service_name}: {exc}") from exc

    async def cleanup_connection(self) -> None:
        """Release any held connection resources."""
        self._connection = None
        self.logger.debug("Connection cleaned up for %s", self.service_name)


__all__ = ["WebSocketConnectionLifecycle", "_validate_connection"]
