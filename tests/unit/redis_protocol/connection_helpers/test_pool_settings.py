"""Tests for pool settings builder."""

from __future__ import annotations

from unittest.mock import patch

from common.redis_protocol.connection_helpers.pool_settings import (
    build_pool_settings,
    mask_sensitive_settings,
)


class TestBuildPoolSettings:
    """Tests for build_pool_settings function."""

    def test_builds_basic_settings(self) -> None:
        """Builds settings with required fields."""
        with patch(
            "common.redis_protocol.connection_helpers.pool_settings.config"
        ) as mock_config:
            mock_config.REDIS_HOST = "localhost"
            mock_config.REDIS_PORT = 6379
            mock_config.REDIS_DB = 0
            mock_config.REDIS_SOCKET_TIMEOUT = 30
            mock_config.REDIS_SOCKET_CONNECT_TIMEOUT = 10
            mock_config.REDIS_SOCKET_KEEPALIVE = True
            mock_config.REDIS_RETRY_ON_TIMEOUT = True
            mock_config.REDIS_HEALTH_CHECK_INTERVAL = 30
            mock_config.REDIS_PASSWORD = None
            mock_config.REDIS_SSL = False

            result = build_pool_settings(50)

            assert result["host"] == "localhost"
            assert result["port"] == 6379
            assert result["max_connections"] == 50
            assert result["decode_responses"] is True

    def test_includes_password_when_set(self) -> None:
        """Includes password in settings when configured."""
        with patch(
            "common.redis_protocol.connection_helpers.pool_settings.config"
        ) as mock_config:
            mock_config.REDIS_HOST = "localhost"
            mock_config.REDIS_PORT = 6379
            mock_config.REDIS_DB = 0
            mock_config.REDIS_SOCKET_TIMEOUT = 30
            mock_config.REDIS_SOCKET_CONNECT_TIMEOUT = 10
            mock_config.REDIS_SOCKET_KEEPALIVE = True
            mock_config.REDIS_RETRY_ON_TIMEOUT = True
            mock_config.REDIS_HEALTH_CHECK_INTERVAL = 30
            mock_config.REDIS_PASSWORD = "secret123"
            mock_config.REDIS_SSL = False

            result = build_pool_settings(50)

            assert result["password"] == "secret123"

    def test_excludes_password_when_empty(self) -> None:
        """Excludes password when not configured."""
        with patch(
            "common.redis_protocol.connection_helpers.pool_settings.config"
        ) as mock_config:
            mock_config.REDIS_HOST = "localhost"
            mock_config.REDIS_PORT = 6379
            mock_config.REDIS_DB = 0
            mock_config.REDIS_SOCKET_TIMEOUT = 30
            mock_config.REDIS_SOCKET_CONNECT_TIMEOUT = 10
            mock_config.REDIS_SOCKET_KEEPALIVE = True
            mock_config.REDIS_RETRY_ON_TIMEOUT = True
            mock_config.REDIS_HEALTH_CHECK_INTERVAL = 30
            mock_config.REDIS_PASSWORD = ""
            mock_config.REDIS_SSL = False

            result = build_pool_settings(50)

            assert "password" not in result

    def test_includes_ssl_when_enabled(self) -> None:
        """Includes SSL setting when enabled."""
        with patch(
            "common.redis_protocol.connection_helpers.pool_settings.config"
        ) as mock_config:
            mock_config.REDIS_HOST = "localhost"
            mock_config.REDIS_PORT = 6379
            mock_config.REDIS_DB = 0
            mock_config.REDIS_SOCKET_TIMEOUT = 30
            mock_config.REDIS_SOCKET_CONNECT_TIMEOUT = 10
            mock_config.REDIS_SOCKET_KEEPALIVE = True
            mock_config.REDIS_RETRY_ON_TIMEOUT = True
            mock_config.REDIS_HEALTH_CHECK_INTERVAL = 30
            mock_config.REDIS_PASSWORD = None
            mock_config.REDIS_SSL = True

            result = build_pool_settings(50)

            assert result["ssl"] is True


class TestMaskSensitiveSettings:
    """Tests for mask_sensitive_settings function."""

    def test_masks_password(self) -> None:
        """Masks password value."""
        settings = {"host": "localhost", "password": "secret123"}

        result = mask_sensitive_settings(settings)

        assert result["password"] == "***"
        assert result["host"] == "localhost"

    def test_does_not_modify_original(self) -> None:
        """Does not modify original settings dict."""
        settings = {"host": "localhost", "password": "secret123"}

        mask_sensitive_settings(settings)

        assert settings["password"] == "secret123"

    def test_handles_settings_without_password(self) -> None:
        """Handles settings without password field."""
        settings = {"host": "localhost", "port": 6379}

        result = mask_sensitive_settings(settings)

        assert result == {"host": "localhost", "port": 6379}
