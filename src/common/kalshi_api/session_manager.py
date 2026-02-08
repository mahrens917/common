"""HTTP session management for Kalshi API client."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

import aiohttp

if TYPE_CHECKING:
    from .client import KalshiConfig


class SessionManager:
    """Manages HTTP session lifecycle for Kalshi API."""

    def __init__(self, config: KalshiConfig) -> None:
        self._config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Ensure the HTTP session is ready."""
        async with self._session_lock:
            if self._session is not None and not self._session.closed:
                return

            timeout = aiohttp.ClientTimeout(
                total=self._config.request_timeout_seconds,
                connect=self._config.connect_timeout_seconds,
                sock_read=self._config.sock_read_timeout_seconds,
            )
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        """Close the HTTP session if one exists."""
        async with self._session_lock:
            if self._session is not None:
                await self._session.close()
                self._session = None

    def get_session(self) -> aiohttp.ClientSession:
        """Get the current session, raising if not initialized."""
        if self._session is None:
            raise RuntimeError("HTTP session not initialized")
        return self._session

    @property
    def session(self) -> Optional[aiohttp.ClientSession]:
        """Access the current session without raising if absent."""
        return self._session

    def set_session(self, value: Optional[aiohttp.ClientSession]) -> None:
        """Override the managed session (used by KalshiClient shims)."""
        self._session = value

    @property
    def session_lock(self) -> asyncio.Lock:
        """Expose the underlying session lock."""
        return self._session_lock

    def set_session_lock(self, lock: asyncio.Lock) -> None:
        """Replace the session lock (tests sometimes inject custom locks)."""
        self._session_lock = lock
