"""Tests for kalshi_api authentication."""

from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from common.kalshi_api.authentication import AuthenticationHelper
from common.kalshi_api.client_helpers.errors import KalshiClientError


def test_init():
    auth = AuthenticationHelper("access_key", "private_key")
    assert auth._access_key == "access_key"
    assert auth._private_key == "private_key"


def test_create_auth_headers_not_rsa():
    auth = AuthenticationHelper("key", "not_an_rsa_key")

    with pytest.raises(KalshiClientError) as exc_info:
        auth.create_auth_headers("GET", "/api/test")

    assert "not RSA" in str(exc_info.value)


def test_create_auth_headers_success():
    mock_private_key = MagicMock(spec=rsa.RSAPrivateKey)
    mock_private_key.sign.return_value = b"signature_bytes"

    auth = AuthenticationHelper("test_access_key", mock_private_key)

    with patch("common.kalshi_api.authentication.time") as mock_time:
        mock_time.time.return_value = 1234567890.123

        headers = auth.create_auth_headers("GET", "/api/v1/markets")

    assert "KALSHI-ACCESS-KEY" in headers
    assert headers["KALSHI-ACCESS-KEY"] == "test_access_key"
    assert "KALSHI-ACCESS-SIGNATURE" in headers
    assert "KALSHI-ACCESS-TIMESTAMP" in headers
    assert headers["KALSHI-ACCESS-TIMESTAMP"] == "1234567890123"

    mock_private_key.sign.assert_called_once()
