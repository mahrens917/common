"""HTTP session management for scraper connection manager."""

import asyncio
import logging
from typing import Optional

import aiohttp

from ..session_tracker import track_existing_session, track_session_close


class ScraperSessionManager:
    """Manages HTTP session lifecycle for scraper services."""

    def __init__(
        self,
        service_name: str,
        user_agent: str,
        connection_timeout_seconds: float,
        request_timeout_seconds: float,
    ):
        """
        Initialize session manager.

        Args:
            service_name: Service identifier
            user_agent: User agent string for requests
            connection_timeout_seconds: Connection timeout
            request_timeout_seconds: Request timeout
        """
        self.service_name = service_name
        self.user_agent = user_agent
        self.connection_timeout_seconds = connection_timeout_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.session: Optional[aiohttp.ClientSession] = None
        self.session_id: Optional[str] = None
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def create_session(self) -> aiohttp.ClientSession:
        """Create HTTP session."""
        if self.session and not self.session.closed:
            await self.close_session()

        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout_seconds,
            connect=self.connection_timeout_seconds,
        )

        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            connector=aiohttp.TCPConnector(
                limit=50,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
                enable_cleanup_closed=True,
            ),
        )

        self.session_id = track_existing_session(self.session, f"{self.service_name}_scraper_manager")
        self.logger.info("Session created and tracked: %s", self.session_id)
        return self.session

    async def close_session(self) -> None:
        """Close HTTP session."""
        if not self.session:
            return

        try:
            if self.session_id:
                track_session_close(self.session_id)
                self.logger.info("Session closure tracked: %s", self.session_id)

            if not self.session.closed:
                self.logger.info("Closing HTTP session")
                connector = getattr(self.session, "connector", None)
                if connector:
                    connector.close()
                    self.logger.debug("Closed connector")
                await asyncio.wait_for(self.session.close(), timeout=5.0)
            else:
                self.logger.debug("HTTP session already closed")
        except (asyncio.TimeoutError, aiohttp.ClientError, OSError):
            self.logger.warning("Error closing HTTP session")
        finally:
            self.session = None
            self.session_id = None
            self.logger.info("HTTP session cleanup completed")

    def is_session_valid(self) -> bool:
        """Check whether the HTTP session is still valid."""
        return self.session is not None and not self.session.closed

    def get_session(self) -> Optional[aiohttp.ClientSession]:
        """Get the current HTTP session."""
        return self.session if self.is_session_valid() else None
