"""Authentication helpers for Kalshi API."""

from __future__ import annotations

import base64
import time
from typing import Any, Dict

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .client_helpers.errors import KalshiClientError


class AuthenticationHelper:
    """Handles authentication for Kalshi API requests."""

    def __init__(self, access_key: str, private_key: Any) -> None:
        """
        Initialize authentication helper.

        Args:
            access_key: Kalshi API access key
            private_key: RSA private key for signing requests
        """
        self._access_key = access_key
        self._private_key = private_key

    def create_auth_headers(self, method: str, path: str) -> Dict[str, str]:
        """
        Generate authentication headers for a request.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path

        Returns:
            Dictionary of authentication headers

        Raises:
            KalshiClientError: If private key is not RSA type
        """
        if not isinstance(self._private_key, rsa.RSAPrivateKey):
            raise KalshiClientError("Loaded private key is not RSA")

        timestamp = str(int(time.time() * 1000))
        message = timestamp + method + path
        signature = self._private_key.sign(
            message.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )

        return {
            "KALSHI-ACCESS-KEY": self._access_key,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }
