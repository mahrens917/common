"""
Scraper connection manager for unified web scraping service management.

This module provides scraper-specific connection management that extends
the base connection manager with web scraping-specific health checks,
HTTP session management, and content validation.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from ..monitor.alerter import Alerter
from .connection_manager import BaseConnectionManager
from .health.types import HealthCheckResult
from .http_utils import AioHTTPSessionConnectionMixin
from .scraper_connection_manager_helpers import (
    ContentValidationHandler,
    ScraperConnectionLifecycle,
    ScraperHealthMonitor,
    ScraperSessionManager,
    ScrapingOperations,
)


class ScraperConnectionManager(AioHTTPSessionConnectionMixin, BaseConnectionManager):
    """Scraper-specific connection manager."""

    def __init__(
        self,
        service_name: str,
        target_urls: List[str],
        content_validators: Optional[List[Callable]] = None,
        user_agent: Optional[str] = None,
        alerter: Optional[Alerter] = None,
    ):
        super().__init__(service_name, alerter)
        self.target_urls = target_urls
        self.user_agent = user_agent or f"{service_name}-scraper/1.0"

        self.session_manager = ScraperSessionManager(
            service_name,
            self.user_agent,
            self.config.connection_timeout_seconds,
            self.config.request_timeout_seconds,
        )
        self.content_validator = ContentValidationHandler(service_name, content_validators)
        self.health_monitor = ScraperHealthMonitor(
            service_name,
            target_urls,
            self.session_manager,
            self.content_validator,
        )
        self.lifecycle_manager = ScraperConnectionLifecycle(
            service_name,
            self.session_manager,
            self.health_monitor,
        )
        self.scraping_ops = ScrapingOperations(
            service_name,
            target_urls,
            self.session_manager,
            self.content_validator,
        )
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def establish_connection(self) -> bool:
        """Establish scraper connection."""
        return await self.lifecycle_manager.establish_connection()

    async def check_connection_health(self) -> HealthCheckResult:
        """Check scraper health."""
        return await self.health_monitor.check_health()

    async def cleanup_connection(self) -> None:
        """Clean up scraper connection."""
        await self.lifecycle_manager.cleanup_connection()

    async def scrape_url(self, url: str, **kwargs) -> Optional[str]:
        """Scrape a single URL."""
        return await self.scraping_ops.scrape_url(url, **kwargs)

    async def scrape_all_urls(self, **kwargs) -> Dict[str, Optional[str]]:
        """Scrape all configured URLs."""
        return await self.scraping_ops.scrape_all_urls(**kwargs)

    def get_connection_info(self) -> Dict[str, Any]:
        """Get scraper connection info and metrics."""
        base_info = self.get_status()
        scraper_info = {
            "target_urls": self.target_urls,
            "is_connected": self.session_manager.is_session_valid(),
            "user_agent": self.user_agent,
        }
        scraper_info.update(self.health_monitor.get_health_details())
        scraper_info.update(self.content_validator.get_validation_metrics())

        session = self.session_manager.get_session()
        if session:
            connector = getattr(session, "_connector", None) or getattr(session, "connector", None)
            connector_info = {}
            if connector:
                # aiohttp stores values on public attributes; tests may supply
                # lightweight doubles that keep the values on private fields.
                def _first_attr(obj, *names):
                    for name in names:
                        if hasattr(obj, name):
                            return getattr(obj, name)
                    return None

                connector_info = {
                    "connection_limit": _first_attr(connector, "_limit", "limit"),
                    "connection_limit_per_host": _first_attr(
                        connector, "_limit_per_host", "limit_per_host"
                    ),
                    "closed": _first_attr(connector, "_closed", "closed"),
                }
            scraper_info.update(
                {"session_closed": session.closed, "connector_info": connector_info}
            )

        base_info["scraper_details"] = scraper_info
        return base_info
