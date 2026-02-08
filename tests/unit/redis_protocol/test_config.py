"""Unit tests for common redis_protocol config module."""

from unittest.mock import MagicMock, patch

import pytest


class TestNormalizeOptionalString:
    """Tests for _normalize_optional_string helper function."""

    def test_normalize_none_returns_none(self):
        """Test that None returns None."""
        from common.redis_protocol.config import _normalize_optional_string

        result = _normalize_optional_string(None)
        assert result is None

    def test_normalize_empty_string_returns_none(self):
        """Test that empty string returns None."""
        from common.redis_protocol.config import _normalize_optional_string

        result = _normalize_optional_string("")
        assert result is None

    def test_normalize_whitespace_string_returns_value(self):
        """Test that whitespace-only string returns the value (it's truthy)."""
        from common.redis_protocol.config import _normalize_optional_string

        result = _normalize_optional_string("   ")
        # Based on the code, "   " would be truthy so it returns the value as-is
        # The function doesn't strip, it just checks truthiness
        assert result == "   "

    def test_normalize_valid_string_returns_string(self):
        """Test that a valid string returns the string."""
        from common.redis_protocol.config import _normalize_optional_string

        result = _normalize_optional_string("password123")
        assert result == "password123"


class TestRedisConnectionSettings:
    """Tests for Redis connection settings loaded from shared configuration."""

    def test_redis_host_is_string(self):
        """Test that REDIS_HOST is a string."""
        from common.redis_protocol import config

        assert isinstance(config.REDIS_HOST, str)
        assert len(config.REDIS_HOST) > 0

    def test_redis_port_is_int(self):
        """Test that REDIS_PORT is an integer."""
        from common.redis_protocol import config

        assert isinstance(config.REDIS_PORT, int)
        assert config.REDIS_PORT > 0

    def test_redis_db_is_int(self):
        """Test that REDIS_DB is an integer."""
        from common.redis_protocol import config

        assert isinstance(config.REDIS_DB, int)
        assert config.REDIS_DB >= 0

    def test_redis_password_is_optional_string(self):
        """Test that REDIS_PASSWORD is either a string or None."""
        from common.redis_protocol import config

        assert config.REDIS_PASSWORD is None or isinstance(config.REDIS_PASSWORD, str)

    def test_redis_ssl_is_boolean(self):
        """Test that REDIS_SSL is a boolean."""
        from common.redis_protocol import config

        assert isinstance(config.REDIS_SSL, bool)

    def test_redis_retry_on_timeout_is_boolean(self):
        """Test that REDIS_RETRY_ON_TIMEOUT is a boolean."""
        from common.redis_protocol import config

        assert isinstance(config.REDIS_RETRY_ON_TIMEOUT, bool)


class TestTimeoutSettings:
    """Tests for timeout settings with environment variable overrides."""

    def test_socket_timeout_is_numeric(self):
        """Test that REDIS_SOCKET_TIMEOUT is a number."""
        from common.redis_protocol import config

        assert isinstance(config.REDIS_SOCKET_TIMEOUT, (int, float))
        assert config.REDIS_SOCKET_TIMEOUT > 0

    def test_connect_timeout_is_numeric(self):
        """Test that REDIS_SOCKET_CONNECT_TIMEOUT is a number."""
        from common.redis_protocol import config

        assert isinstance(config.REDIS_SOCKET_CONNECT_TIMEOUT, (int, float))
        assert config.REDIS_SOCKET_CONNECT_TIMEOUT > 0

    def test_health_check_interval_is_numeric(self):
        """Test that REDIS_HEALTH_CHECK_INTERVAL is a number."""
        from common.redis_protocol import config

        assert isinstance(config.REDIS_HEALTH_CHECK_INTERVAL, (int, float))
        assert config.REDIS_HEALTH_CHECK_INTERVAL > 0


class TestConstantValues:
    """Tests for constant values defined in config."""

    def test_pool_size_constants(self):
        """Test that pool size constants have expected values."""
        from common.redis_protocol import config

        assert config.UNIFIED_POOL_SIZE == 100
        assert config.REDIS_CONNECTION_POOL_SIZE == 10
        assert config.REDIS_CONNECTION_POOL_MAXSIZE == 20

    def test_dns_cache_constants(self):
        """Test that DNS cache constants have expected values."""
        from common.redis_protocol import config

        assert config.REDIS_DNS_CACHE_TTL == 300
        assert config.REDIS_DNS_CACHE_SIZE == 1000

    def test_pdf_settings(self):
        """Test that PDF settings have expected values."""
        from common.redis_protocol import config

        assert config.PDF_SCAN_COUNT == 10000
        assert config.PDF_BATCH_SIZE == 500

    def test_market_collector_settings(self):
        """Test that market collector settings have expected values."""
        from common.redis_protocol import config

        assert config.MARKET_BATCH_SIZE == 1000
        assert config.MARKET_BATCH_TIME_MS == 10
        assert config.MARKET_VERIFY_WRITES is False

    def test_retry_settings(self):
        """Test that retry settings have expected values."""
        from common.redis_protocol import config

        assert config.REDIS_MAX_RETRIES == 3
        assert config.REDIS_RETRY_DELAY == 0.1
        assert config.REDIS_VERIFY_WRITES is True

    def test_socket_keepalive(self):
        """Test that socket keepalive is enabled."""
        from common.redis_protocol import config

        assert config.REDIS_SOCKET_KEEPALIVE is True


class TestKeyPrefixes:
    """Tests for Redis key prefixes and patterns."""

    def test_market_key_prefix_ends_with_colon(self):
        """Test that MARKET_KEY_PREFIX ends with a colon."""
        from common.redis_protocol import config

        assert isinstance(config.MARKET_KEY_PREFIX, str)
        assert config.MARKET_KEY_PREFIX.endswith(":")

    def test_kalshi_market_prefix_ends_with_colon(self):
        """Test that KALSHI_MARKET_PREFIX ends with a colon."""
        from common.redis_protocol import config

        assert isinstance(config.KALSHI_MARKET_PREFIX, str)
        assert config.KALSHI_MARKET_PREFIX.endswith(":")

    def test_subscription_keys(self):
        """Test that subscription keys have expected values."""
        from common.redis_protocol import config

        assert config.DERIBIT_SUBSCRIPTION_KEY == "deribit:subscriptions"
        assert config.KALSHI_SUBSCRIPTION_KEY == "kalshi:subscriptions"

    def test_other_keys(self):
        """Test that other keys have expected values."""
        from common.redis_protocol import config

        assert config.MARKET_LATEST == "deribit_markets:latest"
        assert config.KALSHI_ORDERBOOK_PREFIX == "kalshi:orderbook:"


class TestChannels:
    """Tests for Redis pub/sub channels."""

    def test_subscription_channels(self):
        """Test that subscription channels have expected values."""
        from common.redis_protocol import config

        assert config.DERIBIT_SUBSCRIPTION_CHANNEL == "deribit:subscription:updates"
        assert config.KALSHI_SUBSCRIPTION_CHANNEL == "kalshi:subscription:updates"

    def test_other_channels(self):
        """Test that other channels have expected values."""
        from common.redis_protocol import config

        assert config.PDF_CHANNEL == "pdf:updates"
        assert config.PRICE_INDEX_CHANNEL == "price_index:updates"
        assert config.KALSHI_CHANNEL == "kalshi:updates"


class TestAPITypes:
    """Tests for API type constants."""

    def test_api_type_constants(self):
        """Test that API type constants have expected values."""
        from common.redis_protocol import config

        assert config.API_TYPE_QUOTE == "quote"
        assert config.API_TYPE_PRICE_INDEX == "deribit_price_index"
        assert config.API_TYPE_VOLATILITY_INDEX == "deribit_volatility_index"


class TestHistorySettings:
    """Tests for history tracking settings."""

    def test_history_settings(self):
        """Test that history settings have expected values."""
        from common.redis_protocol import config

        assert config.HISTORY_KEY_PREFIX == "history:"
        assert config.HISTORY_TTL_SECONDS == 7200  # 2 hours (consumers look back 65 minutes max)


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_present(self):
        """Test that all expected exports are present in __all__."""
        from common.redis_protocol import config

        expected_exports = [
            "API_TYPE_PRICE_INDEX",
            "API_TYPE_QUOTE",
            "API_TYPE_VOLATILITY_INDEX",
            "BALANCE_KEY_PREFIX",
            "DATA_CUTOFF_DAYS",
            "DATA_CUTOFF_SECONDS",
            "DERIBIT_SUBSCRIPTION_CHANNEL",
            "DERIBIT_SUBSCRIPTION_KEY",
            "HISTORY_KEY_PREFIX",
            "HISTORY_TTL_SECONDS",
            "KALSHI_BALANCE_KEY",
            "KALSHI_CHANNEL",
            "KALSHI_MARKET_PREFIX",
            "KALSHI_ORDERBOOK_PREFIX",
            "KALSHI_SUBSCRIPTION_CHANNEL",
            "KALSHI_SUBSCRIPTION_KEY",
            "MARKET_BATCH_SIZE",
            "MARKET_BATCH_TIME_MS",
            "MARKET_KEY_PREFIX",
            "MARKET_LATEST",
            "MARKET_VERIFY_WRITES",
            "PDF_BATCH_SIZE",
            "PDF_CHANNEL",
            "PDF_SCAN_COUNT",
            "PRICE_INDEX_CHANNEL",
            "REDIS_CONNECTION_POOL_MAXSIZE",
            "REDIS_CONNECTION_POOL_SIZE",
            "REDIS_DB",
            "REDIS_PASSWORD",
            "REDIS_DNS_CACHE_SIZE",
            "REDIS_DNS_CACHE_TTL",
            "REDIS_HEALTH_CHECK_INTERVAL",
            "REDIS_HOST",
            "REDIS_MAX_RETRIES",
            "REDIS_PORT",
            "REDIS_RETRY_DELAY",
            "REDIS_RETRY_ON_TIMEOUT",
            "REDIS_SSL",
            "REDIS_SOCKET_CONNECT_TIMEOUT",
            "REDIS_SOCKET_KEEPALIVE",
            "REDIS_SOCKET_TIMEOUT",
            "REDIS_VERIFY_WRITES",
            "UNIFIED_POOL_SIZE",
        ]

        assert config.__all__ == expected_exports

    def test_all_exports_are_accessible(self):
        """Test that all items in __all__ are accessible as module attributes."""
        from common.redis_protocol import config

        for export_name in config.__all__:
            assert hasattr(config, export_name), f"Missing export: {export_name}"


class TestDefaultConstants:
    """Tests for default constant values."""

    def test_default_timeout_constants(self):
        """Test that default timeout constants have expected values."""
        from common.redis_protocol import config

        assert config.DEFAULT_SOCKET_TIMEOUT_SECONDS == 10
        assert config.DEFAULT_CONNECT_TIMEOUT_SECONDS == 10
        assert config.DEFAULT_HEALTH_CHECK_INTERVAL_SECONDS == 15
