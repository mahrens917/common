"""WebSocket message operations."""

import asyncio
import logging
from typing import Optional

from websockets import WebSocketException


class WebSocketMessageOperations:
    """Handles WebSocket message sending/receiving."""

    def __init__(self, service_name: str, connection_provider):
        self.service_name = service_name
        self.connection_provider = connection_provider
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def send_message(self, message: str) -> bool:
        """Send message through WebSocket."""
        websocket = self.connection_provider.get_connection()
        if not websocket or websocket.close_code is not None:
            self.logger.error("Cannot send message - WebSocket not connected")
            return False

        try:
            await websocket.send(message)
            self.logger.debug(f"Sent message: {message[:100]}...")
        except WebSocketException:
            self.logger.exception(f"Failed to send message: ")
            return False
        except (OSError, RuntimeError, ValueError):
            self.logger.exception(f"Unexpected error sending message: ")
            return False
        else:
            return True

    async def receive_message(self, timeout: Optional[float] = None) -> Optional[str]:
        """Receive message from WebSocket."""
        websocket = self.connection_provider.get_connection()
        if not websocket or websocket.close_code is not None:
            self.logger.error("Cannot receive message - WebSocket not connected")
            return None

        try:
            if timeout:
                raw_message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            else:
                raw_message = await websocket.recv()

            if isinstance(raw_message, bytes):
                message = raw_message.decode("utf-8", errors="replace")
            else:
                message = str(raw_message)

            self.logger.debug(f"Received message: {str(message)[:100]}...")

        except asyncio.TimeoutError:
            self.logger.debug("Receive timeout")
            return None
        except WebSocketException:
            self.logger.exception(f"Failed to receive message: ")
            return None
        except (OSError, RuntimeError, ValueError):
            self.logger.exception(f"Unexpected error receiving message: ")
            return None
        else:
            return message
