"""
Network error detection and classification.

This module provides canonical detection of network-level failures
versus application-level errors. All modules should import from here
rather than implementing their own detection.
"""

import asyncio
import socket

import aiohttp

NETWORK_ERROR_TYPES = (
    aiohttp.ClientConnectorError,
    aiohttp.ClientProxyConnectionError,
    aiohttp.ClientConnectorSSLError,
    aiohttp.ClientConnectorCertificateError,
    aiohttp.ServerTimeoutError,
    aiohttp.ClientHttpProxyError,
    asyncio.TimeoutError,
    socket.gaierror,
    OSError,
)


def is_network_unreachable_error(exception: BaseException) -> bool:
    """
    Determine if an exception represents a network connectivity failure.

    Args:
        exception: Exception to check

    Returns:
        True if this is a network-level error that indicates connectivity issues
    """
    if isinstance(exception, NETWORK_ERROR_TYPES):
        return True

    os_error = getattr(exception, "os_error", None)
    return isinstance(os_error, OSError)


__all__ = ["is_network_unreachable_error", "NETWORK_ERROR_TYPES"]
