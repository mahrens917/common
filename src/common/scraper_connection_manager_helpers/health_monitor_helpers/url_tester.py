"""URL health testing logic."""

import asyncio
import logging

import aiohttp

from src.common.config_loader import load_config
from src.common.constants.time import HEALTH_CHECK_TIMEOUT

VALIDATION_CONFIG = load_config("validation_constants.json")


class URLTester:
    """Tests individual URLs for health."""

    def __init__(self, logger: logging.Logger):
        """Initialize URL tester."""
        self.logger = logger

    async def test_url(self, url: str, session: aiohttp.ClientSession, content_validator) -> bool:
        """Test a single URL for health."""
        try:
            self.logger.debug(f"Health checking URL: {url}")
            health_timeout = aiohttp.ClientTimeout(total=30.0)

            async with session.get(url, timeout=health_timeout) as response:
                if not (
                    VALIDATION_CONFIG["api_response"]["http_ok"]
                    <= response.status
                    < HEALTH_CHECK_TIMEOUT
                ):
                    self.logger.warning(f"URL unhealthy: {url} (HTTP {response.status})")
                    return False

                return await self._validate_response_content(url, response, content_validator)

        except asyncio.TimeoutError:
            self.logger.warning(f"Health check timeout: {url}")
            return False
        except aiohttp.ClientError as exc:
            self.logger.warning(f"Health check client error: {url} - {exc}")
            return False
        except (RuntimeError, ValueError, UnicodeDecodeError):
            self.logger.exception(f"Unexpected health check error:  - ")
            return False

    async def _validate_response_content(
        self, url: str, response: aiohttp.ClientResponse, content_validator
    ) -> bool:
        """Validate response content if validator is configured."""
        if not content_validator.has_validators():
            return True

        content = await response.text()
        is_valid = await content_validator.validate_content(content, url)

        if is_valid:
            self.logger.debug(f"URL healthy: {url}")
        else:
            self.logger.warning(f"Content validation failed: {url}")

        return is_valid
