"""Tests for kalshi_api component_initializer."""

from unittest.mock import MagicMock, patch

from common.kalshi_api.client import KalshiConfig
from common.kalshi_api.client_helpers.component_initializer import ComponentInitializer


def test_init():
    config = KalshiConfig()
    initializer = ComponentInitializer(config)
    assert initializer.config is config


def test_initialize():
    config = KalshiConfig()
    initializer = ComponentInitializer(config)

    with patch("common.kalshi_api.client_helpers.component_initializer.SessionManager") as mock_sm:
        with patch("common.kalshi_api.client_helpers.component_initializer.AuthenticationHelper") as mock_auth:
            with patch("common.kalshi_api.client_helpers.component_initializer.RequestBuilder") as mock_rb:
                with patch("common.kalshi_api.client_helpers.component_initializer.ResponseParser") as mock_rp:
                    with patch("common.kalshi_api.client_helpers.component_initializer.PortfolioOperations") as mock_po:
                        with patch("common.kalshi_api.client_helpers.component_initializer.OrderOperations") as mock_oo:
                            mock_sm.return_value = MagicMock()
                            mock_auth.return_value = MagicMock()
                            mock_rb.return_value = MagicMock()
                            mock_rp.return_value = MagicMock()
                            mock_po.return_value = MagicMock()
                            mock_oo.return_value = MagicMock()

                            result = initializer.initialize("access_key", MagicMock())

                            assert "session_manager" in result
                            assert "auth_helper" in result
                            assert "request_builder" in result
                            assert "response_parser" in result
                            assert "portfolio_ops" in result
                            assert "order_ops" in result
