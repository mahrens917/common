"""Tests for pool validator module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.redis_protocol.connection_helpers.pool_validator import (
    REDIS_SETUP_ERRORS,
    test_pool_connection,
)


class TestRedisSetupErrors:
    """Tests for REDIS_SETUP_ERRORS constant."""

    def test_contains_expected_error_types(self) -> None:
        """Contains expected error types."""
        from redis.exceptions import RedisError

        assert RedisError in REDIS_SETUP_ERRORS
        assert ConnectionError in REDIS_SETUP_ERRORS
        assert TimeoutError in REDIS_SETUP_ERRORS
        assert asyncio.TimeoutError in REDIS_SETUP_ERRORS
        assert OSError in REDIS_SETUP_ERRORS
        assert RuntimeError in REDIS_SETUP_ERRORS
        assert ValueError in REDIS_SETUP_ERRORS


class TestTestPoolConnection:
    """Tests for test_pool_connection function."""

    @pytest.mark.asyncio
    async def test_success_closes_client(self) -> None:
        """Closes test client after successful ping."""
        mock_pool = MagicMock()
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {"redis_version": "7.0.0", "redis_mode": "standalone"}

        with patch(
            "src.common.redis_protocol.connection_helpers.pool_validator.redis.asyncio.Redis"
        ) as mock_redis:
            mock_redis.return_value = mock_client

            await test_pool_connection(mock_pool, "localhost", 6379, 0)

            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self) -> None:
        """Raises RuntimeError on connection timeout."""
        mock_pool = MagicMock()
        mock_client = AsyncMock()
        mock_client.ping.side_effect = asyncio.TimeoutError()

        with patch(
            "src.common.redis_protocol.connection_helpers.pool_validator.redis.asyncio.Redis"
        ) as mock_redis:
            mock_redis.return_value = mock_client

            with pytest.raises(RuntimeError) as exc_info:
                await test_pool_connection(mock_pool, "localhost", 6379, 0)

            assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_on_connection_error(self) -> None:
        """Raises RuntimeError on connection error."""
        mock_pool = MagicMock()
        mock_client = AsyncMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")

        with patch(
            "src.common.redis_protocol.connection_helpers.pool_validator.redis.asyncio.Redis"
        ) as mock_redis:
            with patch("src.common.redis_protocol.connection_helpers.pool_validator.logger"):
                mock_redis.return_value = mock_client

                with pytest.raises(RuntimeError) as exc_info:
                    await test_pool_connection(mock_pool, "localhost", 6379, 0)

                assert "Redis pool creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_closes_client_on_error(self) -> None:
        """Closes test client even when ping fails."""
        mock_pool = MagicMock()
        mock_client = AsyncMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")

        with patch(
            "src.common.redis_protocol.connection_helpers.pool_validator.redis.asyncio.Redis"
        ) as mock_redis:
            with patch("src.common.redis_protocol.connection_helpers.pool_validator.logger"):
                mock_redis.return_value = mock_client

                with pytest.raises(RuntimeError):
                    await test_pool_connection(mock_pool, "localhost", 6379, 0)

                mock_client.aclose.assert_called_once()
