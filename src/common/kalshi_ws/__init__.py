"""Kalshi WebSocket client library.

Shared WebSocket client implementation for Kalshi API integration.
Used by: peak, kalshi, and other trading system repositories.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Optional

from common.constants.network import HTTP_OK

# Constants for avoiding literal fallbacks in ternary expressions
EMPTY_API_KEY_SECRET: str = ""
EMPTY_PARAMS: dict = {}
NESTED_MARKETS_PARAMS: dict = {"with_nested_markets": "true"}

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger(__name__)

# Try to import websockets module for re-export
try:
    import websockets
    from websockets import exceptions as websockets_exceptions

    def _resolve_status_exception():
        """Get the appropriate handshake status exception."""
        invalid_status = getattr(websockets_exceptions, "InvalidStatus", None)
        if invalid_status is not None:
            return invalid_status
        return getattr(websockets_exceptions, "InvalidStatusCode", None)

    WebsocketStatusException = _resolve_status_exception()
except ModuleNotFoundError:
    websockets = None  # type: ignore[assignment]
    websockets_exceptions = None  # type: ignore[assignment]
    WebsocketStatusException = None  # type: ignore[assignment]


class KalshiWSClientError(RuntimeError):
    """Base error for Kalshi websocket client failures.

    Supports attaching arbitrary keyword fields as attributes.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message)
        for key, value in kwargs.items():
            setattr(self, key, value)


class KalshiWSConnectionError(KalshiWSClientError):
    """Raised when the websocket connection fails."""


class KalshiWSConfigurationError(KalshiWSClientError):
    """Raised when required websocket client configuration is missing or invalid."""


class KalshiWSSigningError(KalshiWSClientError):
    """Raised when websocket signing fails."""


class KalshiWSHTTPError(KalshiWSClientError):
    """Raised when REST calls from the websocket client fail."""


class ConnectionState(Enum):
    """WebSocket connection state."""

    DISCONNECTED = auto()
    CONNECTED = auto()
    AUTHENTICATED = auto()
    SUBSCRIBED = auto()


@dataclass(frozen=True)
class KalshiCredentials:
    """Kalshi API credentials."""

    key_id: str
    api_key_secret: str
    rsa_private_key: Optional[str]

    def require_private_key(self) -> str:
        """Return the private key or raise if not set."""
        if not self.rsa_private_key:
            raise KalshiWSConfigurationError("KALSHI_RSA_PRIVATE_KEY is required")
        return self.rsa_private_key


@lru_cache(maxsize=1)
def get_kalshi_credentials(*, require_secret: bool = True) -> KalshiCredentials:
    """Get Kalshi credentials from environment."""
    import os

    key_id = os.environ.get("KALSHI_KEY_ID")
    if not key_id:
        raise KalshiWSConfigurationError("KALSHI_KEY_ID must be set")
    api_key_secret_env = os.environ.get("KALSHI_API_KEY_SECRET")
    api_key_secret = api_key_secret_env if api_key_secret_env is not None else EMPTY_API_KEY_SECRET
    if require_secret and not api_key_secret:
        raise KalshiWSConfigurationError("KALSHI_API_KEY_SECRET must be provided")
    private_key = os.environ.get("KALSHI_RSA_PRIVATE_KEY")

    return KalshiCredentials(
        key_id=key_id,
        api_key_secret=api_key_secret,
        rsa_private_key=private_key,
    )


class AuthenticationManager:
    """Manage authentication and request signing for Kalshi WebSocket."""

    def __init__(self, api_key_id: Optional[str] = None, api_key_secret: Optional[str] = None):
        """Initialize authentication manager."""
        self._credentials = get_kalshi_credentials(require_secret=False)
        self.api_key_id = api_key_id or self._credentials.key_id
        self.api_key_secret = api_key_secret or self._credentials.api_key_secret

        if not self.api_key_id:
            raise KalshiWSConfigurationError("API key ID must be provided")

        self.private_key = self._load_private_key()

    def _load_private_key(self) -> "rsa.RSAPrivateKey":
        """Load and validate RSA private key."""
        import os
        from pathlib import Path

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        from common.config import ConfigurationError

        try:
            key_value = self._credentials.require_private_key()
        except ConfigurationError as exc:
            raise KalshiWSConfigurationError(str(exc)) from exc

        try:
            # Check if it's a file path
            if key_value.startswith("/") or key_value.startswith("~"):
                key_path = Path(os.path.expanduser(key_value))
                key_bytes = key_path.read_bytes()
            else:
                # Treat as base64-encoded key content
                key_bytes = base64.b64decode(key_value)
            private_key = serialization.load_pem_private_key(key_bytes, password=None)
        except Exception as exc:
            raise KalshiWSConfigurationError(f"Failed to load private key: {exc}") from exc

        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise KalshiWSConfigurationError("Loaded private key is not an RSA private key")

        return private_key

    def get_auth_headers(self, method: str, path: str, params: Optional[dict] = None) -> dict:
        """Generate authentication headers for API request."""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        timestamp = str(int(time.time() * 1000))
        msg_string = timestamp + method + path

        try:
            signature = self.private_key.sign(
                msg_string.encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
        except Exception as exc:
            raise KalshiWSSigningError("RSA sign PSS failed") from exc

        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

    def validate_credentials(self):
        """Validate credentials by generating test headers."""
        self.get_auth_headers("GET", "/test")
        return True


class ConnectionHandler:
    """Handle WebSocket connection lifecycle."""

    def __init__(self, auth_manager: AuthenticationManager, config: Any):
        """Initialize connection handler."""
        self.auth_manager = auth_manager
        self.config = config
        self.ws_url = "wss://api.elections.kalshi.com/trade-api/ws/v2"
        self.ws: Optional[Any] = None
        self.state = ConnectionState.DISCONNECTED

    def set_authenticated(self) -> None:
        """Set state to authenticated."""
        self.state = ConnectionState.AUTHENTICATED

    async def connect_websocket(self):
        """Connect to Kalshi websocket."""
        import websockets
        from websockets import exceptions as ws_exceptions

        if self.state != ConnectionState.AUTHENTICATED:
            raise KalshiWSConnectionError("Client must be authenticated before connecting")

        path = "/trade-api/ws/v2"
        headers = self.auth_manager.get_auth_headers("GET", path)

        # Get status exception class
        status_exc = getattr(ws_exceptions, "InvalidStatus", None)
        if status_exc is None:
            status_exc = getattr(ws_exceptions, "InvalidStatusCode", None)

        try:
            ws = await websockets.connect(
                self.ws_url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=20,
                max_size=None,
                close_timeout=self.config.connection_timeout_seconds // 3,
            )
        except Exception as exc:
            # Check if it's a status exception
            if status_exc is not None and isinstance(exc, status_exc):
                if "401" in str(exc):
                    raise KalshiWSConnectionError("Authentication failed (HTTP 401). Check API key and private key") from exc
                raise KalshiWSConnectionError("Websocket connection returned invalid status code") from exc
            raise KalshiWSConnectionError("Failed to connect to Kalshi websocket") from exc

        if self.ws is not None:
            await self.close()
        self.ws = ws
        self.state = ConnectionState.CONNECTED
        return ws

    async def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.ws = None
        self.state = ConnectionState.DISCONNECTED


class APIRequestHandler:
    """Handle REST API requests."""

    def __init__(self, auth_manager: AuthenticationManager, config: Any):
        """Initialize API request handler."""
        self.auth_manager = auth_manager
        self.config = config
        self.base_url = "https://api.elections.kalshi.com"

    async def get_event(self, event_ticker: str, with_nested_markets: bool = False):
        """Get event details from Kalshi API."""
        import aiohttp

        params = NESTED_MARKETS_PARAMS if with_nested_markets else EMPTY_PARAMS
        path = f"/trade-api/v2/events/{event_ticker}"
        url = self.base_url + path
        headers = self.auth_manager.get_auth_headers("GET", path)

        try:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_seconds * 2)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                ) as response:
                    if response.status != HTTP_OK:
                        text = await response.text()
                        raise KalshiWSHTTPError(f"Failed to get event {event_ticker}: {response.status} - {text}")
                    return await response.json()
        except asyncio.TimeoutError as exc:
            raise KalshiWSHTTPError(f"API request timed out while fetching event {event_ticker}") from exc
        except aiohttp.ClientError as exc:
            raise KalshiWSHTTPError(f"HTTP error while fetching event {event_ticker}") from exc


class KalshiWebsocketClient:
    """Kalshi WebSocket client with authentication and API support."""

    def __init__(self, api_key_id: Optional[str] = None, api_key_secret: Optional[str] = None):
        """Initialize Kalshi WebSocket client."""
        from common.connection_config import get_connection_config

        self.auth_token: Optional[str] = None
        self.config = get_connection_config("kalshi")

        self.auth_manager = AuthenticationManager(api_key_id, api_key_secret)
        self.connection_handler = ConnectionHandler(self.auth_manager, self.config)
        self.api_client = APIRequestHandler(self.auth_manager, self.config)
        self.private_key = self.auth_manager.private_key

    async def initialize(self):
        """Initialize client and validate credentials."""
        self.auth_manager.validate_credentials()
        self.connection_handler.set_authenticated()
        return True

    async def connect_websocket(self):
        """Connect to Kalshi websocket."""
        return await self.connection_handler.connect_websocket()

    async def close(self):
        """Close the client connection."""
        await self.connection_handler.close()

    async def get_event(self, event_ticker: str, with_nested_markets: bool = False):
        """Get event details from Kalshi API."""
        return await self.api_client.get_event(event_ticker, with_nested_markets)

    @property
    def state(self) -> ConnectionState:
        """Expose current connection state."""
        return self.connection_handler.state

    @state.setter
    def state(self, value: ConnectionState) -> None:
        self.connection_handler.state = value

    @property
    def ws(self):
        """Expose active websocket connection if present."""
        return self.connection_handler.ws

    @ws.setter
    def ws(self, value) -> None:
        self.connection_handler.ws = value


__all__ = [
    "APIRequestHandler",
    "AuthenticationManager",
    "ConnectionHandler",
    "ConnectionState",
    "KalshiCredentials",
    "KalshiWebsocketClient",
    "KalshiWSClientError",
    "KalshiWSConfigurationError",
    "KalshiWSConnectionError",
    "KalshiWSHTTPError",
    "KalshiWSSigningError",
    "WebsocketStatusException",
    "get_kalshi_credentials",
    "websockets",
    "websockets_exceptions",
]
