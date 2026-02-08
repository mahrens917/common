"""Tests for kalshi_api client."""

from unittest.mock import MagicMock, patch

import pytest

from common.kalshi_api.client import KalshiClient, KalshiConfig, _session, _session_setter


class TestKalshiConfig:
    def test_defaults(self):
        config = KalshiConfig()
        assert config.base_url == "https://api.elections.kalshi.com"
        assert config.request_timeout_seconds == 30
        assert config.connect_timeout_seconds == 10
        assert config.network_max_retries == 3
        assert config.network_backoff_base_seconds == 1.0
        assert config.network_backoff_max_seconds == 30.0

    def test_custom_values(self):
        config = KalshiConfig(
            base_url="https://custom.api.com",
            request_timeout_seconds=30,
            connect_timeout_seconds=20,
            network_max_retries=5,
            network_backoff_base_seconds=2.0,
            network_backoff_max_seconds=60.0,
        )
        assert config.base_url == "https://custom.api.com"
        assert config.request_timeout_seconds == 30


class TestKalshiClientInit:
    def test_init_creates_components(self):
        mock_credentials = MagicMock()
        mock_credentials.key_id = "test_key"
        mock_credentials.secret = "test_secret"

        mock_private_key = MagicMock()
        mock_session_lock = MagicMock()

        mock_session_manager = MagicMock()
        mock_session_manager.session_lock = mock_session_lock

        mock_components = {
            "session_manager": mock_session_manager,
            "auth_helper": MagicMock(),
            "request_builder": MagicMock(),
            "response_parser": MagicMock(),
            "portfolio_ops": MagicMock(),
            "order_ops": MagicMock(),
        }

        with patch("common.kalshi_api.client.get_kalshi_credentials") as mock_get_creds:
            with patch("common.kalshi_api.client.CredentialValidator") as mock_validator:
                with patch("common.kalshi_api.client.KeyLoader") as mock_loader:
                    with patch("common.kalshi_api.client.ComponentInitializer") as mock_init:
                        mock_get_creds.return_value = mock_credentials
                        mock_validator.extract_and_validate.return_value = "base64_key"
                        mock_loader.load_private_key.return_value = mock_private_key
                        mock_init.return_value.initialize.return_value = mock_components

                        client = KalshiClient()

                        assert client._config.base_url == "https://api.elections.kalshi.com"
                        assert client._access_key == "test_key"
                        assert client._private_key is mock_private_key
                        assert client._initialized is False
                        mock_get_creds.assert_called_once_with(require_secret=False)
                        mock_validator.extract_and_validate.assert_called_once_with(mock_credentials)
                        mock_loader.load_private_key.assert_called_once_with("base64_key")

    def test_init_with_custom_config(self):
        mock_credentials = MagicMock()
        mock_credentials.key_id = "test_key"
        mock_credentials.secret = "test_secret"

        mock_private_key = MagicMock()
        mock_session_lock = MagicMock()

        mock_session_manager = MagicMock()
        mock_session_manager.session_lock = mock_session_lock

        mock_components = {
            "session_manager": mock_session_manager,
            "auth_helper": MagicMock(),
            "request_builder": MagicMock(),
            "response_parser": MagicMock(),
            "portfolio_ops": MagicMock(),
            "order_ops": MagicMock(),
        }

        custom_config = KalshiConfig(base_url="https://custom.api.com")

        with patch("common.kalshi_api.client.get_kalshi_credentials") as mock_get_creds:
            with patch("common.kalshi_api.client.CredentialValidator") as mock_validator:
                with patch("common.kalshi_api.client.KeyLoader") as mock_loader:
                    with patch("common.kalshi_api.client.ComponentInitializer") as mock_init:
                        mock_get_creds.return_value = mock_credentials
                        mock_validator.extract_and_validate.return_value = "base64_key"
                        mock_loader.load_private_key.return_value = mock_private_key
                        mock_init.return_value.initialize.return_value = mock_components

                        client = KalshiClient(config=custom_config)

                        assert client._config.base_url == "https://custom.api.com"

    def test_init_with_trade_store(self):
        mock_credentials = MagicMock()
        mock_credentials.key_id = "test_key"
        mock_credentials.secret = "test_secret"

        mock_private_key = MagicMock()
        mock_session_lock = MagicMock()

        mock_session_manager = MagicMock()
        mock_session_manager.session_lock = mock_session_lock

        mock_order_ops = MagicMock()

        mock_components = {
            "session_manager": mock_session_manager,
            "auth_helper": MagicMock(),
            "request_builder": MagicMock(),
            "response_parser": MagicMock(),
            "portfolio_ops": MagicMock(),
            "order_ops": mock_order_ops,
        }

        mock_trade_store = MagicMock()

        with patch("common.kalshi_api.client.get_kalshi_credentials") as mock_get_creds:
            with patch("common.kalshi_api.client.CredentialValidator") as mock_validator:
                with patch("common.kalshi_api.client.KeyLoader") as mock_loader:
                    with patch("common.kalshi_api.client.ComponentInitializer") as mock_init:
                        mock_get_creds.return_value = mock_credentials
                        mock_validator.extract_and_validate.return_value = "base64_key"
                        mock_loader.load_private_key.return_value = mock_private_key
                        mock_init.return_value.initialize.return_value = mock_components

                        client = KalshiClient(trade_store=mock_trade_store)

                        # The attach_trade_store method should have been called
                        assert client._trade_store is mock_trade_store


class TestSessionProperty:
    def test_session_not_initialized(self):
        class MockObj:
            pass

        obj = MockObj()

        with pytest.raises(RuntimeError) as exc_info:
            _session(obj)

        assert "not initialized" in str(exc_info.value)

    def test_session_manager_none(self):
        class MockObj:
            pass

        obj = MockObj()
        obj.__dict__["_session_manager"] = None

        with pytest.raises(RuntimeError) as exc_info:
            _session(obj)

        assert "not initialized" in str(exc_info.value)

    def test_session_cached(self):
        class MockObj:
            pass

        mock_session = MagicMock()
        obj = MockObj()
        obj.__dict__["_session_manager"] = MagicMock()
        obj.__dict__["_cached_session"] = mock_session

        result = _session(obj)

        assert result is mock_session

    def test_session_from_manager(self):
        class MockObj:
            pass

        mock_session = MagicMock()
        mock_manager = MagicMock()
        mock_manager.session = mock_session

        obj = MockObj()
        obj.__dict__["_session_manager"] = mock_manager

        result = _session(obj)

        assert result is mock_session
        assert obj.__dict__["_cached_session"] is mock_session


class TestSessionSetter:
    def test_setter_no_manager(self):
        class MockObj:
            pass

        obj = MockObj()
        mock_session = MagicMock()

        _session_setter(obj, mock_session)

        assert obj.__dict__["_cached_session"] is mock_session

    def test_setter_manager_none(self):
        class MockObj:
            pass

        obj = MockObj()
        obj.__dict__["_session_manager"] = None

        with pytest.raises(RuntimeError) as exc_info:
            _session_setter(obj, MagicMock())

        assert "not initialized" in str(exc_info.value)

    def test_setter_with_manager(self):
        mock_session = MagicMock()
        mock_manager = MagicMock()

        class MockObj:
            pass

        obj = MockObj()
        obj.__dict__["_session_manager"] = mock_manager

        _session_setter(obj, mock_session)

        mock_manager.set_session.assert_called_once_with(mock_session)
        assert obj.__dict__["_cached_session"] is mock_session
