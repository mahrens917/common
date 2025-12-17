"""Tests for the kalshi_ws module."""

import pytest

from common.kalshi_ws import (
    ConnectionState,
    KalshiCredentials,
    KalshiWSClientError,
    KalshiWSConfigurationError,
    KalshiWSConnectionError,
    KalshiWSHTTPError,
    KalshiWSSigningError,
)


class TestConnectionState:
    """Tests for ConnectionState enum."""

    def test_connection_state_disconnected(self):
        assert ConnectionState.DISCONNECTED.name == "DISCONNECTED"

    def test_connection_state_connected(self):
        assert ConnectionState.CONNECTED.name == "CONNECTED"

    def test_connection_state_authenticated(self):
        assert ConnectionState.AUTHENTICATED.name == "AUTHENTICATED"

    def test_connection_state_subscribed(self):
        assert ConnectionState.SUBSCRIBED.name == "SUBSCRIBED"


class TestKalshiCredentials:
    """Tests for KalshiCredentials dataclass."""

    def test_credentials_creation(self):
        creds = KalshiCredentials(
            key_id="test_key",
            api_key_secret="test_secret",
            rsa_private_key="test_private_key",
        )
        assert creds.key_id == "test_key"
        assert creds.api_key_secret == "test_secret"
        assert creds.rsa_private_key == "test_private_key"

    def test_credentials_require_private_key_success(self):
        creds = KalshiCredentials(
            key_id="test_key",
            api_key_secret="test_secret",
            rsa_private_key="test_private_key",
        )
        result = creds.require_private_key()
        assert result == "test_private_key"

    def test_credentials_require_private_key_raises_when_none(self):
        creds = KalshiCredentials(
            key_id="test_key",
            api_key_secret="test_secret",
            rsa_private_key=None,
        )
        with pytest.raises(KalshiWSConfigurationError) as exc_info:
            creds.require_private_key()
        assert "KALSHI_RSA_PRIVATE_KEY is required" in str(exc_info.value)


class TestKalshiWSClientError:
    """Tests for KalshiWSClientError base exception."""

    def test_error_message(self):
        error = KalshiWSClientError("Test error message")
        assert str(error) == "Test error message"

    def test_error_with_kwargs(self):
        error = KalshiWSClientError("Test error", code=123, detail="extra info")
        assert str(error) == "Test error"
        assert error.code == 123
        assert error.detail == "extra info"


class TestKalshiWSConnectionError:
    """Tests for KalshiWSConnectionError exception."""

    def test_connection_error_inherits_from_client_error(self):
        error = KalshiWSConnectionError("Connection failed")
        assert isinstance(error, KalshiWSClientError)

    def test_connection_error_message(self):
        error = KalshiWSConnectionError("Connection failed")
        assert str(error) == "Connection failed"


class TestKalshiWSConfigurationError:
    """Tests for KalshiWSConfigurationError exception."""

    def test_configuration_error_inherits_from_client_error(self):
        error = KalshiWSConfigurationError("Invalid config")
        assert isinstance(error, KalshiWSClientError)

    def test_configuration_error_message(self):
        error = KalshiWSConfigurationError("Invalid config")
        assert str(error) == "Invalid config"


class TestKalshiWSSigningError:
    """Tests for KalshiWSSigningError exception."""

    def test_signing_error_inherits_from_client_error(self):
        error = KalshiWSSigningError("Signing failed")
        assert isinstance(error, KalshiWSClientError)

    def test_signing_error_message(self):
        error = KalshiWSSigningError("Signing failed")
        assert str(error) == "Signing failed"


class TestKalshiWSHTTPError:
    """Tests for KalshiWSHTTPError exception."""

    def test_http_error_inherits_from_client_error(self):
        error = KalshiWSHTTPError("HTTP request failed")
        assert isinstance(error, KalshiWSClientError)

    def test_http_error_message(self):
        error = KalshiWSHTTPError("HTTP request failed")
        assert str(error) == "HTTP request failed"

    def test_http_error_with_status_code(self):
        error = KalshiWSHTTPError("HTTP request failed", status_code=404)
        assert str(error) == "HTTP request failed"
        assert error.status_code == 404
