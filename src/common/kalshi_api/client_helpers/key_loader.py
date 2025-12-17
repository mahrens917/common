"""Load and validate RSA private keys."""

from __future__ import annotations

import base64
import binascii
import os
from pathlib import Path

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from .errors import KalshiClientError


class KeyLoader:
    """Load and validate RSA private keys."""

    @staticmethod
    def load_private_key(private_key_value: str):
        """Load and validate RSA private key from base64 string, PEM text, or file path."""
        key_bytes = _resolve_key_bytes(private_key_value)

        try:
            return serialization.load_pem_private_key(
                key_bytes,
                password=None,
                backend=default_backend(),
            )
        except (ValueError, TypeError, UnsupportedAlgorithm, RuntimeError) as exc:
            raise KalshiClientError("Failed to load Kalshi RSA private key") from exc


def _resolve_key_bytes(value: str) -> bytes:
    """Resolve key material from base64, inline PEM, or filesystem paths."""
    if not value:
        raise KalshiClientError("Kalshi RSA private key is not configured")

    expanded = os.path.expanduser(value.strip())
    if os.path.exists(expanded):
        return Path(expanded).read_bytes()

    if "BEGIN" in value:
        return value.encode("utf-8")

    try:
        return base64.b64decode(value)
    except (ValueError, binascii.Error) as exc:
        raise KalshiClientError("Kalshi RSA key is not valid base64") from exc
