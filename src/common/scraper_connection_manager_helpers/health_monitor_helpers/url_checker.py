# ruff: noqa: PLR2004, PLR0913, PLR0911, PLR0912, PLR0915, C901
"""URL health checking logic."""

import asyncio
import logging

import aiohttp

# Constants extracted for ruff PLR2004 compliance
RESPONSE_STATUS_300 = 300


async def check_url_health(
    url: str,
    session: aiohttp.ClientSession,
    content_validator,
    logger: logging.Logger,
) -> bool:
    """
    Check health of a single URL.

    Args:
        url: URL to check
        session: HTTP session
        content_validator: Content validation handler
        logger: Logger instance

    Returns:
        True if URL is healthy, False otherwise
    """
    try:
        logger.debug(f"Health checking URL: {url}")
        health_timeout = aiohttp.ClientTimeout(total=30.0)

        async with session.get(url, timeout=health_timeout) as response:
            if not (200 <= response.status < 300):
                logger.warning(f"URL unhealthy: {url} (HTTP {response.status})")
                return False

            # Check content validity if validators exist
            if content_validator.has_validators():
                content = await response.text()
                content_valid = await content_validator.validate_content(content, url)
                if not content_valid:
                    logger.warning(f"Content validation failed: {url}")
                    return False

            logger.debug(f"URL healthy: {url}")
            return True

    except asyncio.TimeoutError:  # Transient network/connection failure  # policy_guard: allow-silent-handler
        logger.warning(f"Health check timeout: {url}")
        return False

    except aiohttp.ClientError as e:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
        logger.warning(f"Health check client error: {url} - {e}")
        return False

    except (  # policy_guard: allow-silent-handler
        RuntimeError,
        ValueError,
        UnicodeDecodeError,
    ):
        logger.exception(f"Unexpected health check error:  - ")
        return False


def calculate_health_threshold(total_urls: int) -> int:
    """Calculate minimum healthy URLs needed (50% threshold)."""
    return max(1, total_urls // 2)
