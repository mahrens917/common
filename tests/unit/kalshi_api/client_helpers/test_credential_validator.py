"""Tests for kalshi_api credential_validator."""

from unittest.mock import MagicMock

import pytest

from common.kalshi_api.client_helpers.credential_validator import CredentialValidator
from common.kalshi_api.client_helpers.errors import KalshiClientError


def test_extract_and_validate_success():
    credentials = MagicMock()
    credentials.require_private_key.return_value = "private_key_data"

    result = CredentialValidator.extract_and_validate(credentials)

    assert result == "private_key_data"
    credentials.require_private_key.assert_called_once()


def test_extract_and_validate_runtime_error():
    credentials = MagicMock()
    credentials.require_private_key.side_effect = RuntimeError("missing key")

    with pytest.raises(KalshiClientError) as exc_info:
        CredentialValidator.extract_and_validate(credentials)

    assert "missing key" in str(exc_info.value)
