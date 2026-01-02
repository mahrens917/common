"""Tests for network error detection."""

import asyncio
import socket

import aiohttp
import pytest

from common.network_errors import NETWORK_ERROR_TYPES, is_network_unreachable_error


class TestNetworkErrorTypes:
    """Tests for NETWORK_ERROR_TYPES constant."""

    def test_network_error_types_is_tuple(self) -> None:
        """Test that NETWORK_ERROR_TYPES is a tuple."""
        assert isinstance(NETWORK_ERROR_TYPES, tuple)

    def test_network_error_types_contains_expected_errors(self) -> None:
        """Test that NETWORK_ERROR_TYPES contains expected error classes."""
        assert aiohttp.ClientConnectorError in NETWORK_ERROR_TYPES
        assert aiohttp.ClientProxyConnectionError in NETWORK_ERROR_TYPES
        assert aiohttp.ClientConnectorSSLError in NETWORK_ERROR_TYPES
        assert aiohttp.ClientConnectorCertificateError in NETWORK_ERROR_TYPES
        assert aiohttp.ServerTimeoutError in NETWORK_ERROR_TYPES
        assert aiohttp.ClientHttpProxyError in NETWORK_ERROR_TYPES
        assert asyncio.TimeoutError in NETWORK_ERROR_TYPES
        assert socket.gaierror in NETWORK_ERROR_TYPES
        assert OSError in NETWORK_ERROR_TYPES


class TestIsNetworkUnreachableError:
    """Tests for is_network_unreachable_error function."""

    def test_aiohttp_connector_error(self) -> None:
        """Test detection of aiohttp.ClientConnectorError."""
        error = aiohttp.ClientConnectorError(connection_key=None, os_error=OSError("Connection failed"))
        assert is_network_unreachable_error(error) is True

    def test_aiohttp_proxy_connection_error(self) -> None:
        """Test detection of aiohttp.ClientProxyConnectionError."""
        error = aiohttp.ClientProxyConnectionError(connection_key=None, os_error=OSError("Proxy connection failed"))
        assert is_network_unreachable_error(error) is True

    def test_aiohttp_timeout_error(self) -> None:
        """Test detection of aiohttp.ServerTimeoutError."""
        error = aiohttp.ServerTimeoutError()
        assert is_network_unreachable_error(error) is True

    def test_asyncio_timeout_error(self) -> None:
        """Test detection of asyncio.TimeoutError."""
        error = asyncio.TimeoutError()
        assert is_network_unreachable_error(error) is True

    def test_socket_gaierror(self) -> None:
        """Test detection of socket.gaierror."""
        error = socket.gaierror("DNS resolution failed")
        assert is_network_unreachable_error(error) is True

    def test_oserror(self) -> None:
        """Test detection of OSError."""
        error = OSError("Network unreachable")
        assert is_network_unreachable_error(error) is True

    def test_exception_with_os_error_attribute(self) -> None:
        """Test detection of exception with os_error attribute."""

        class CustomException(Exception):
            """Custom exception with os_error attribute."""

            def __init__(self) -> None:
                super().__init__()
                self.os_error = OSError("Network issue")

        error = CustomException()
        assert is_network_unreachable_error(error) is True

    def test_non_network_error(self) -> None:
        """Test that non-network errors return False."""
        error = ValueError("Not a network error")
        assert is_network_unreachable_error(error) is False

    def test_exception_with_non_oserror_attribute(self) -> None:
        """Test exception with non-OSError os_error attribute."""

        class CustomException(Exception):
            """Custom exception with non-OSError os_error."""

            def __init__(self) -> None:
                super().__init__()
                self.os_error = ValueError("Not an OS error")

        error = CustomException()
        assert is_network_unreachable_error(error) is False
