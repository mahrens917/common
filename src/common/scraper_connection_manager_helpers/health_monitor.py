"""Health monitoring for scraper connection manager."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from ..health.types import BaseHealthMonitor, HealthCheckResult

# Constants
_CONST_300 = 300
_TEMP_MAX = 200


class ScraperHealthMonitor(BaseHealthMonitor):
    """Monitors health of target URLs for scraper service."""

    def __init__(self, service_name: str, target_urls: List[str], session_provider, content_validator):
        super().__init__(service_name)
        self.target_urls = target_urls
        self.session_provider = session_provider
        self.content_validator = content_validator
        self.url_health_status: Dict[str, bool] = {}
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def check_health(self) -> HealthCheckResult:
        """Return True when at least half the URLs respond with healthy content."""
        session = self.session_provider.get_session()
        if not session or session.closed:
            self.logger.warning("HTTP session is closed")
            self.record_failure()
            return HealthCheckResult(False, details=self.get_health_details(), error="session_closed")

        loop = asyncio.get_running_loop()
        healthy_urls = await _evaluate_urls(self, session, loop)
        is_healthy = _record_health_outcome(self, healthy_urls, loop)
        result = HealthCheckResult(
            is_healthy,
            details=self.get_health_details(),
            error=None if is_healthy else "insufficient_healthy_urls",
        )
        return result

    def clear_health_status(self) -> None:
        self.url_health_status.clear()

    def get_health_details(self) -> Dict[str, Any]:
        return {
            "url_health_status": self.url_health_status.copy(),
            "last_successful_scrape_time": self.last_success_time,
            "consecutive_scrape_failures": self.consecutive_failures,
        }


async def _evaluate_urls(monitor: "ScraperHealthMonitor", session, loop) -> int:
    healthy_urls = 0
    for url in monitor.target_urls:
        if await _check_single_url(monitor, session, url, loop):
            healthy_urls += 1
    return healthy_urls


async def _check_single_url(monitor: "ScraperHealthMonitor", session, url: str, loop) -> bool:
    try:
        monitor.logger.debug("Health checking URL: %s", url)
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30.0)) as response:
            return await _handle_response(monitor, url, response, loop)
    except asyncio.TimeoutError:
        _mark_url_unhealthy(monitor, url, "Health check timeout")
    except aiohttp.ClientError as exc:
        _mark_url_unhealthy(monitor, url, f"Health check client error: {exc}")
    except (RuntimeError, ValueError, UnicodeDecodeError):
        monitor.logger.exception("Unexpected health check error for %s", url)
        _mark_url_unhealthy(monitor, url, None)
    return False


async def _handle_response(monitor: "ScraperHealthMonitor", url, response, loop) -> bool:
    if not (_TEMP_MAX <= response.status < _CONST_300):
        _mark_url_unhealthy(monitor, url, f"HTTP {response.status}")
        return False

    if monitor.content_validator.has_validators():
        content = await response.text()
        is_valid = await monitor.content_validator.validate_content(content, url)
        if not is_valid:
            _mark_url_unhealthy(monitor, url, "Content validation failed")
            return False

    monitor.url_health_status[url] = True
    monitor.record_success(timestamp=loop.time())
    monitor.logger.debug("URL healthy: %s", url)
    return True


def _mark_url_unhealthy(monitor: "ScraperHealthMonitor", url: str, reason: Optional[str]) -> None:
    monitor.url_health_status[url] = False
    if reason:
        monitor.logger.warning("%s: %s", reason, url)


def _record_health_outcome(monitor: "ScraperHealthMonitor", healthy_urls: int, loop) -> bool:
    total_urls = len(monitor.target_urls)
    health_threshold = max(1, total_urls // 2)
    is_healthy = healthy_urls >= health_threshold

    if is_healthy:
        monitor.record_success(timestamp=loop.time())
        monitor.logger.debug("Health check passed: %d/%d URLs healthy", healthy_urls, total_urls)
    else:
        monitor.record_failure()
        monitor.logger.warning(
            "Health check failed: only %d/%d URLs healthy (need %d)",
            healthy_urls,
            total_urls,
            health_threshold,
        )
    return is_healthy
