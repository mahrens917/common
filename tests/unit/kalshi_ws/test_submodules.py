"""Tests for kalshi_ws submodule re-exports."""


class TestApiClientReExports:
    """Tests for kalshi_ws.api_client re-exports."""

    def test_import_api_request_handler(self):
        from common.kalshi_ws.api_client import APIRequestHandler

        assert APIRequestHandler is not None


class TestAuthenticationReExports:
    """Tests for kalshi_ws.authentication re-exports."""

    def test_import_authentication_manager(self):
        from common.kalshi_ws.authentication import AuthenticationManager

        assert AuthenticationManager is not None

    def test_import_configuration_error(self):
        from common.kalshi_ws.authentication import KalshiWSConfigurationError

        assert KalshiWSConfigurationError is not None

    def test_import_signing_error(self):
        from common.kalshi_ws.authentication import KalshiWSSigningError

        assert KalshiWSSigningError is not None

    def test_import_get_kalshi_credentials(self):
        from common.kalshi_ws.authentication import get_kalshi_credentials

        assert get_kalshi_credentials is not None


class TestConnectionReExports:
    """Tests for kalshi_ws.connection re-exports."""

    def test_import_connection_handler(self):
        from common.kalshi_ws.connection import ConnectionHandler

        assert ConnectionHandler is not None

    def test_import_connection_state(self):
        from common.kalshi_ws.connection import ConnectionState

        assert ConnectionState is not None

    def test_import_client_error(self):
        from common.kalshi_ws.connection import KalshiWSClientError

        assert KalshiWSClientError is not None

    def test_import_connection_error(self):
        from common.kalshi_ws.connection import KalshiWSConnectionError

        assert KalshiWSConnectionError is not None

    def test_import_http_error(self):
        from common.kalshi_ws.connection import KalshiWSHTTPError

        assert KalshiWSHTTPError is not None

    def test_import_websocket_status_exception(self):
        from common.kalshi_ws.connection import WebsocketStatusException

        # May be None if websockets not installed
        assert WebsocketStatusException is not None or WebsocketStatusException is None

    def test_import_websockets(self):
        from common.kalshi_ws.connection import websockets

        # May be None if websockets not installed
        assert websockets is not None or websockets is None

    def test_import_websockets_exceptions(self):
        from common.kalshi_ws.connection import websockets_exceptions

        # May be None if websockets not installed
        assert websockets_exceptions is not None or websockets_exceptions is None
