"""Tests for kalshi_api client_helpers credential_validator."""

import pytest

from common.kalshi_api.client_helpers.errors import KalshiClientError
from common.kalshi_api.client_helpers.key_loader import extract_and_validate_credentials


class _CredentialsOk:
    def require_private_key(self):
        return "base64encodedkey=="


class _CredentialsBad:
    def require_private_key(self):
        raise RuntimeError("private key not set")


def test_extract_and_validate_credentials_success():
    result = extract_and_validate_credentials(_CredentialsOk())
    assert result == "base64encodedkey=="


def test_extract_and_validate_credentials_raises_client_error():
    with pytest.raises(KalshiClientError, match="private key not set"):
        extract_and_validate_credentials(_CredentialsBad())
