"""Tests for trade_visualizer_helpers.redis_helpers.connection module."""

from unittest.mock import MagicMock, patch

from common.trade_visualizer_helpers.redis_helpers.connection import (
    get_redis_connection,
    get_schema_config,
)


class TestGetRedisConnection:
    """Tests for get_redis_connection function."""

    def test_delegates_to_redis_utils(self) -> None:
        """Test delegates to common.redis_utils and returns its result."""
        mock_func = MagicMock()
        mock_func.return_value = "mock_connection"

        with patch(
            "common.redis_utils.get_redis_connection",
            mock_func,
        ):
            result = get_redis_connection()

        assert result == "mock_connection"
        mock_func.assert_called_once()


class TestGetSchemaConfig:
    """Tests for get_schema_config function."""

    def test_delegates_to_config_module(self) -> None:
        """Test delegates to common.config.redis_schema."""
        mock_config = {"key": "value"}

        with patch(
            "common.config.redis_schema.get_schema_config",
            return_value=mock_config,
        ):
            result = get_schema_config()

        assert result == mock_config
