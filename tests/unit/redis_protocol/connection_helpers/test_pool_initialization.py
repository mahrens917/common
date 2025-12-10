"""Tests for pool initialization module."""

import asyncio
import weakref
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.connection_helpers.pool_initialization import create_and_test_pool


class TestCreateAndTestPool:
    """Tests for create_and_test_pool function."""

    @pytest.mark.asyncio
    async def test_returns_pool_and_loop_ref(self) -> None:
        """Returns tuple of pool and weak loop reference."""
        current_loop = asyncio.get_event_loop()

        with patch(
            "common.redis_protocol.connection_helpers.pool_initialization.build_pool_settings"
        ) as mock_settings:
            with patch(
                "common.redis_protocol.connection_helpers.pool_initialization.mask_sensitive_settings"
            ) as mock_mask:
                with patch(
                    "common.redis_protocol.connection_helpers.pool_initialization.redis.asyncio.ConnectionPool"
                ) as mock_pool_cls:
                    with patch(
                        "common.redis_protocol.connection_helpers.pool_initialization.test_pool_connection"
                    ) as mock_test:
                        mock_settings.return_value = {"max_connections": 10}
                        mock_mask.return_value = {"max_connections": 10}
                        mock_pool = MagicMock()
                        mock_pool_cls.return_value = mock_pool
                        mock_test.return_value = None

                        pool, pool_loop = await create_and_test_pool(
                            10, "localhost", 6379, 0, current_loop
                        )

                        assert pool is mock_pool
                        assert pool_loop() is current_loop

    @pytest.mark.asyncio
    async def test_calls_test_pool_connection(self) -> None:
        """Calls test_pool_connection with pool and settings."""
        current_loop = asyncio.get_event_loop()

        with patch(
            "common.redis_protocol.connection_helpers.pool_initialization.build_pool_settings"
        ) as mock_settings:
            with patch(
                "common.redis_protocol.connection_helpers.pool_initialization.mask_sensitive_settings"
            ):
                with patch(
                    "common.redis_protocol.connection_helpers.pool_initialization.redis.asyncio.ConnectionPool"
                ) as mock_pool_cls:
                    with patch(
                        "common.redis_protocol.connection_helpers.pool_initialization.test_pool_connection"
                    ) as mock_test:
                        mock_settings.return_value = {}
                        mock_pool = MagicMock()
                        mock_pool_cls.return_value = mock_pool

                        await create_and_test_pool(10, "localhost", 6379, 0, current_loop)

                        mock_test.assert_called_once_with(mock_pool, "localhost", 6379, 0)

    @pytest.mark.asyncio
    async def test_propagates_test_failure(self) -> None:
        """Propagates RuntimeError from test_pool_connection."""
        current_loop = asyncio.get_event_loop()

        with patch(
            "common.redis_protocol.connection_helpers.pool_initialization.build_pool_settings"
        ) as mock_settings:
            with patch(
                "common.redis_protocol.connection_helpers.pool_initialization.mask_sensitive_settings"
            ):
                with patch(
                    "common.redis_protocol.connection_helpers.pool_initialization.redis.asyncio.ConnectionPool"
                ):
                    with patch(
                        "common.redis_protocol.connection_helpers.pool_initialization.test_pool_connection"
                    ) as mock_test:
                        mock_settings.return_value = {}
                        mock_test.side_effect = RuntimeError("Connection failed")

                        with pytest.raises(RuntimeError) as exc_info:
                            await create_and_test_pool(10, "localhost", 6379, 0, current_loop)

                        assert "Connection failed" in str(exc_info.value)
