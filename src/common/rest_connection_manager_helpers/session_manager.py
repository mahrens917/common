"""REST HTTP session management."""

import asyncio
import logging
from typing import Optional

import aiohttp

from ..session_tracker import track_existing_session, track_session_close


class RESTSessionManager:
    """Manages HTTP session for REST connections."""

    def __init__(
        self,
        service_name: str,
        connection_timeout: float,
        request_timeout: float,
        track_creation=track_existing_session,
        track_close=track_session_close,
    ):
        self.service_name = service_name
        self.connection_timeout = connection_timeout
        self.request_timeout = request_timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.session_id: Optional[str] = None
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
        self._track_creation = track_creation
        self._track_close = track_close

    async def create_session(self) -> aiohttp.ClientSession:
        """Create HTTP session."""
        if self.session and not self.session.closed:
            await self.close_session()

        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout,
            connect=self.connection_timeout,
        )

        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": f"{self.service_name}-client/1.0"},
            connector=aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
            ),
        )

        self.session_id = self._track_creation(self.session, f"{self.service_name}_rest_manager")
        self.logger.info(f"Session created and tracked: {self.session_id}")
        return self.session

    async def close_session(self) -> None:
        """Close HTTP session."""
        if not self.session:
            return

        try:
            if self.session_id:
                self._track_close(self.session_id)
                self.logger.info(f"Session closure tracked: {self.session_id}")

            if not self.session.closed:
                self.logger.info("Closing HTTP session")
                connector = getattr(self.session, "connector", None)
                if connector:
                    connector.close()
                    self.logger.debug("Closed connector")
                await asyncio.wait_for(self.session.close(), timeout=5.0)
            else:
                self.logger.debug("HTTP session already closed")

        except (aiohttp.ClientError, asyncio.TimeoutError, OSError):  # policy_guard: allow-silent-handler
            self.logger.warning(f"Error closing HTTP session")
        finally:
            self.session = None
            self.session_id = None
            self.logger.info("HTTP session cleanup completed")

    def get_session(self) -> Optional[aiohttp.ClientSession]:
        """Get current session."""
        return self.session if self.session and not self.session.closed else None
