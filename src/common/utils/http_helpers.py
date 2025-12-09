"""Utilities for HTTP client session creation and management."""

from typing import Dict, Optional

import aiohttp


def build_http_session(
    *,
    timeout_seconds: float,
    user_agent: str,
    additional_headers: Optional[Dict[str, str]] = None,
) -> aiohttp.ClientSession:
    """
    Create an aiohttp ClientSession with standard configuration.

    Args:
        timeout_seconds: Total request timeout in seconds
        user_agent: User-Agent header value
        additional_headers: Optional additional headers to include

    Returns:
        Configured aiohttp.ClientSession

    Example:
        >>> session = build_http_session(
        ...     timeout_seconds=30.0,
        ...     user_agent="MyApp/1.0",
        ...     additional_headers={"Accept": "application/json"}
        ... )
    """
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    headers = {"User-Agent": user_agent}

    if additional_headers:
        headers.update(additional_headers)

    return aiohttp.ClientSession(timeout=timeout, headers=headers)


__all__ = ["build_http_session"]
