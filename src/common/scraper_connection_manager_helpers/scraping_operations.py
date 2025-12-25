'"""Scraping operations for scraper connection manager."""'

import asyncio
import logging
from typing import Dict, List, Optional

import aiohttp

# Constants
_CONST_300 = 300
_TEMP_MAX = 200


class ScrapingOperations:
    """Handles scraping operations for URLs."""

    def __init__(
        self,
        service_name: str,
        target_urls: List[str],
        session_provider,
        content_validator,
    ):
        """
        Initialize scraping operations.

        Args:
            service_name: Service identifier
            target_urls: List of URLs to scrape
            session_provider: Provider for HTTP session
            content_validator: Content validation handler
        """
        self.service_name = service_name
        self.target_urls = target_urls
        self.session_provider = session_provider
        self.content_validator = content_validator
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def scrape_url(self, url: str, **kwargs) -> Optional[str]:
        """Scrape a single URL."""
        session = self.session_provider.get_session()
        if not session or session.closed:
            self.logger.error("Cannot scrape - session not connected")
            return None

        try:
            self.logger.debug("Scraping URL: %s", url)
            async with session.get(url, **kwargs) as response:
                if _TEMP_MAX <= response.status < _CONST_300:
                    content = await response.text()
                    if self.content_validator.has_validators():
                        content_valid = await self.content_validator.validate_content(content, url)
                        if not content_valid:
                            self.logger.warning("Scraped content validation failed for %s", url)
                            return None
                    self.logger.debug("Successfully scraped %s characters from %s", len(content), url)
                    return content
                self.logger.warning("Scraping failed for %s: HTTP %s", url, response.status)
                return None
        except aiohttp.ClientError:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            self.logger.exception("Scraping client error for %s", url)
            return None
        except (
            RuntimeError,
            ValueError,
            UnicodeDecodeError,
        ):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            self.logger.exception("Unexpected scraping error for %s", url)
            return None

    async def scrape_all_urls(self, **kwargs) -> Dict[str, Optional[str]]:
        """Scrape all configured URLs."""
        if not self.session_provider.is_session_valid():
            self.logger.error("Cannot scrape - session not connected")
            return {}

        scraping_tasks = [asyncio.create_task(self.scrape_url(url, **kwargs)) for url in self.target_urls]
        results = await asyncio.gather(*scraping_tasks, return_exceptions=True)

        scraped_content: Dict[str, Optional[str]] = {}
        for url, result in zip(self.target_urls, results):
            if isinstance(result, BaseException):
                self.logger.error("Scraping task failed for %s: %s", url, result)
                scraped_content[url] = None
            else:
                scraped_content[url] = result

        successful_scrapes = sum(1 for content in scraped_content.values() if content is not None)
        self.logger.info("Scraped %s/%s URLs", successful_scrapes, len(self.target_urls))
        return scraped_content
