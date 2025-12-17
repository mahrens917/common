"""Tests for kalshi_api key_loader."""

import base64
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from common.kalshi_api.client_helpers.errors import KalshiClientError
from common.kalshi_api.client_helpers.key_loader import KeyLoader, _resolve_key_bytes


def _generate_test_pem() -> bytes:
    """Generate a test RSA private key in PEM format."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def test_load_private_key_from_pem_string():
    pem_bytes = _generate_test_pem()
    pem_str = pem_bytes.decode("utf-8")

    key = KeyLoader.load_private_key(pem_str)

    assert isinstance(key, rsa.RSAPrivateKey)


def test_load_private_key_from_base64():
    pem_bytes = _generate_test_pem()
    b64_str = base64.b64encode(pem_bytes).decode("utf-8")

    key = KeyLoader.load_private_key(b64_str)

    assert isinstance(key, rsa.RSAPrivateKey)


def test_load_private_key_from_file():
    pem_bytes = _generate_test_pem()
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pem") as f:
        f.write(pem_bytes)
        temp_path = f.name

    try:
        key = KeyLoader.load_private_key(temp_path)
        assert isinstance(key, rsa.RSAPrivateKey)
    finally:
        Path(temp_path).unlink()


def test_load_private_key_invalid_key():
    with pytest.raises(KalshiClientError) as exc_info:
        KeyLoader.load_private_key(base64.b64encode(b"not a key").decode())

    assert "Failed to load" in str(exc_info.value)


def test_resolve_key_bytes_empty():
    with pytest.raises(KalshiClientError) as exc_info:
        _resolve_key_bytes("")

    assert "not configured" in str(exc_info.value)


def test_resolve_key_bytes_invalid_base64():
    with pytest.raises(KalshiClientError) as exc_info:
        _resolve_key_bytes("not!valid!base64!!!")

    assert "not valid base64" in str(exc_info.value)


def test_resolve_key_bytes_pem_inline():
    pem_text = "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
    result = _resolve_key_bytes(pem_text)
    assert result == pem_text.encode("utf-8")


def test_resolve_key_bytes_file_path():
    pem_bytes = _generate_test_pem()
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pem") as f:
        f.write(pem_bytes)
        temp_path = f.name

    try:
        result = _resolve_key_bytes(temp_path)
        assert result == pem_bytes
    finally:
        Path(temp_path).unlink()
