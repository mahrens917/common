"""Tests for Redis connection wrapper utilities."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

from common.redis_protocol.connection_wrappers import (
    RedisConnection,
    RedisConnectionManager,
)


class _FakeRedisClient:
    """Fake Redis client for testing."""

    def __init__(self, *, should_fail_ping: bool = False):
        self.should_fail_ping = should_fail_ping
        self.ping_called = False
        self.aclose_called = False

    async def ping(self):
        """Fake ping method."""
        self.ping_called = True
        if self.should_fail_ping:
            raise RedisConnectionError("Connection failed")
        return True

    async def aclose(self):
        """Fake aclose method."""
        self.aclose_called = True


@pytest.mark.asyncio
async def test_redis_connection_connect_establishes_connection():
    """Test that connect establishes a Redis connection."""
    fake_client = _FakeRedisClient()

    with (
        patch(
            "common.redis_protocol.connection_wrappers.get_redis_client",
            new_callable=AsyncMock,
            return_value=fake_client,
        ) as mock_get_client,
        patch("common.redis_protocol.connection_wrappers.record_pool_acquired") as mock_record,
    ):
        conn = RedisConnection()
        result = await conn.connect()

        assert result is fake_client
        assert fake_client.ping_called
        mock_get_client.assert_awaited_once()
        mock_record.assert_called_once()


@pytest.mark.asyncio
async def test_redis_connection_connect_reuses_existing_client():
    """Test that connect reuses existing client if already connected."""
    fake_client = _FakeRedisClient()

    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        return_value=fake_client,
    ) as mock_get_client:
        conn = RedisConnection()
        result1 = await conn.connect()
        fake_client.ping_called = False
        result2 = await conn.connect()

        assert result1 is fake_client
        assert result2 is fake_client
        assert not fake_client.ping_called
        assert mock_get_client.await_count == 1


@pytest.mark.asyncio
async def test_redis_connection_connect_raises_on_connection_error():
    """Test that connect raises ConnectionError on Redis connection failure."""
    fake_client = _FakeRedisClient(should_fail_ping=True)

    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        return_value=fake_client,
    ):
        conn = RedisConnection()

        with pytest.raises(ConnectionError, match="Redis connection failed"):
            await conn.connect()


@pytest.mark.asyncio
async def test_redis_connection_connect_handles_redis_error():
    """Test that connect handles RedisError during connection."""
    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        side_effect=RedisError("Redis error"),
    ):
        conn = RedisConnection()

        with pytest.raises(ConnectionError, match="Redis connection failed"):
            await conn.connect()


@pytest.mark.asyncio
async def test_redis_connection_connect_handles_timeout_error():
    """Test that connect handles TimeoutError during connection."""
    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        side_effect=RedisTimeoutError("Timeout"),
    ):
        conn = RedisConnection()

        with pytest.raises(ConnectionError, match="Redis connection failed"):
            await conn.connect()


@pytest.mark.asyncio
async def test_redis_connection_connect_handles_runtime_error():
    """Test that connect handles RuntimeError during connection."""
    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Runtime error"),
    ):
        conn = RedisConnection()

        with pytest.raises(ConnectionError, match="Redis connection failed"):
            await conn.connect()


@pytest.mark.asyncio
async def test_redis_connection_get_client_connects_if_not_connected():
    """Test that get_client connects if not already connected."""
    fake_client = _FakeRedisClient()

    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        return_value=fake_client,
    ):
        conn = RedisConnection()
        result = await conn.get_client()

        assert result is fake_client
        assert fake_client.ping_called


@pytest.mark.asyncio
async def test_redis_connection_get_client_returns_existing_client():
    """Test that get_client returns existing client if connected."""
    fake_client = _FakeRedisClient()

    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        return_value=fake_client,
    ):
        conn = RedisConnection()
        await conn.connect()
        fake_client.ping_called = False
        result = await conn.get_client()

        assert result is fake_client
        assert not fake_client.ping_called


@pytest.mark.asyncio
async def test_redis_connection_close_closes_client():
    """Test that close properly closes the Redis client."""
    fake_client = _FakeRedisClient()

    with (
        patch(
            "common.redis_protocol.connection_wrappers.get_redis_client",
            new_callable=AsyncMock,
            return_value=fake_client,
        ),
        patch("common.redis_protocol.connection_wrappers.record_pool_returned") as mock_record,
    ):
        conn = RedisConnection()
        await conn.connect()
        await conn.close()

        assert fake_client.aclose_called
        mock_record.assert_called_once()


@pytest.mark.asyncio
async def test_redis_connection_close_resets_client_reference():
    """Test that close resets internal client reference."""
    fake_client = _FakeRedisClient()

    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        return_value=fake_client,
    ):
        conn = RedisConnection()
        await conn.connect()
        await conn.close()

        assert conn._client is None


@pytest.mark.asyncio
async def test_redis_connection_close_handles_no_client():
    """Test that close handles case where no client exists."""
    conn = RedisConnection()
    await conn.close()
    assert conn._client is None


@pytest.mark.asyncio
async def test_redis_connection_close_handles_redis_error():
    """Test that close handles RedisError during close."""
    fake_client = _FakeRedisClient()

    async def _failing_aclose():
        raise RedisError("Close error")

    fake_client.aclose = _failing_aclose

    with (
        patch(
            "common.redis_protocol.connection_wrappers.get_redis_client",
            new_callable=AsyncMock,
            return_value=fake_client,
        ),
        patch("common.redis_protocol.connection_wrappers.logger"),
    ):
        conn = RedisConnection()
        await conn.connect()
        await conn.close()

        assert conn._client is None


@pytest.mark.asyncio
async def test_redis_connection_close_handles_connection_error():
    """Test that close handles ConnectionError during close."""
    fake_client = _FakeRedisClient()

    async def _failing_aclose():
        raise RedisConnectionError("Close connection error")

    fake_client.aclose = _failing_aclose

    with (
        patch(
            "common.redis_protocol.connection_wrappers.get_redis_client",
            new_callable=AsyncMock,
            return_value=fake_client,
        ),
        patch("common.redis_protocol.connection_wrappers.logger"),
    ):
        conn = RedisConnection()
        await conn.connect()
        await conn.close()

        assert conn._client is None


@pytest.mark.asyncio
async def test_redis_connection_manager_get_connection_establishes_connection():
    """Test that get_connection establishes a Redis connection."""
    fake_client = _FakeRedisClient()

    with (
        patch(
            "common.redis_protocol.connection_wrappers.get_redis_client",
            new_callable=AsyncMock,
            return_value=fake_client,
        ) as mock_get_client,
        patch("common.redis_protocol.connection_wrappers.record_pool_acquired") as mock_record,
    ):
        manager = RedisConnectionManager()
        result = await manager.get_connection()

        assert result is fake_client
        mock_get_client.assert_awaited_once()
        mock_record.assert_called_once()


@pytest.mark.asyncio
async def test_redis_connection_manager_get_connection_reuses_existing():
    """Test that get_connection reuses existing connection."""
    fake_client = _FakeRedisClient()

    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        return_value=fake_client,
    ) as mock_get_client:
        manager = RedisConnectionManager()
        result1 = await manager.get_connection()
        result2 = await manager.get_connection()

        assert result1 is fake_client
        assert result2 is fake_client
        assert mock_get_client.await_count == 1


@pytest.mark.asyncio
async def test_redis_connection_manager_get_connection_raises_on_error():
    """Test that get_connection raises ConnectionError on failure."""
    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        side_effect=RedisConnectionError("Connection failed"),
    ):
        manager = RedisConnectionManager()

        with pytest.raises(ConnectionError, match="Redis connection failed"):
            await manager.get_connection()


@pytest.mark.asyncio
async def test_redis_connection_manager_get_connection_handles_timeout():
    """Test that get_connection handles timeout errors."""
    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        side_effect=RedisTimeoutError("Timeout"),
    ):
        manager = RedisConnectionManager()

        with pytest.raises(ConnectionError, match="Redis connection failed"):
            await manager.get_connection()


@pytest.mark.asyncio
async def test_redis_connection_manager_get_connection_handles_oserror():
    """Test that get_connection handles OSError."""
    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        side_effect=OSError("OS error"),
    ):
        manager = RedisConnectionManager()

        with pytest.raises(ConnectionError, match="Redis connection failed"):
            await manager.get_connection()


@pytest.mark.asyncio
async def test_redis_connection_manager_get_connection_handles_value_error():
    """Test that get_connection handles ValueError."""
    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        side_effect=ValueError("Value error"),
    ):
        manager = RedisConnectionManager()

        with pytest.raises(ConnectionError, match="Redis connection failed"):
            await manager.get_connection()


@pytest.mark.asyncio
async def test_redis_connection_manager_close_closes_connection():
    """Test that close properly closes the connection."""
    fake_client = _FakeRedisClient()

    with (
        patch(
            "common.redis_protocol.connection_wrappers.get_redis_client",
            new_callable=AsyncMock,
            return_value=fake_client,
        ),
        patch("common.redis_protocol.connection_wrappers.record_pool_returned") as mock_record,
    ):
        manager = RedisConnectionManager()
        await manager.get_connection()
        await manager.close()

        assert fake_client.aclose_called
        mock_record.assert_called_once()


@pytest.mark.asyncio
async def test_redis_connection_manager_close_resets_connection_reference():
    """Test that close resets internal connection reference."""
    fake_client = _FakeRedisClient()

    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        return_value=fake_client,
    ):
        manager = RedisConnectionManager()
        await manager.get_connection()
        await manager.close()

        assert manager._connection is None


@pytest.mark.asyncio
async def test_redis_connection_manager_close_handles_no_connection():
    """Test that close handles case where no connection exists."""
    manager = RedisConnectionManager()
    await manager.close()
    assert manager._connection is None


@pytest.mark.asyncio
async def test_redis_connection_manager_close_handles_redis_error():
    """Test that close handles RedisError during close."""
    fake_client = _FakeRedisClient()

    async def _failing_aclose():
        raise RedisError("Close error")

    fake_client.aclose = _failing_aclose

    with (
        patch(
            "common.redis_protocol.connection_wrappers.get_redis_client",
            new_callable=AsyncMock,
            return_value=fake_client,
        ),
        patch("common.redis_protocol.connection_wrappers.logger"),
    ):
        manager = RedisConnectionManager()
        await manager.get_connection()
        await manager.close()

        assert manager._connection is None


@pytest.mark.asyncio
async def test_redis_connection_manager_close_handles_connection_error():
    """Test that close handles ConnectionError during close."""
    fake_client = _FakeRedisClient()

    async def _failing_aclose():
        raise RedisConnectionError("Close connection error")

    fake_client.aclose = _failing_aclose

    with (
        patch(
            "common.redis_protocol.connection_wrappers.get_redis_client",
            new_callable=AsyncMock,
            return_value=fake_client,
        ),
        patch("common.redis_protocol.connection_wrappers.logger"),
    ):
        manager = RedisConnectionManager()
        await manager.get_connection()
        await manager.close()

        assert manager._connection is None


@pytest.mark.asyncio
async def test_redis_connection_manager_close_handles_timeout_error():
    """Test that close handles TimeoutError during close."""
    fake_client = _FakeRedisClient()

    async def _failing_aclose():
        raise RedisTimeoutError("Close timeout")

    fake_client.aclose = _failing_aclose

    with (
        patch(
            "common.redis_protocol.connection_wrappers.get_redis_client",
            new_callable=AsyncMock,
            return_value=fake_client,
        ),
        patch("common.redis_protocol.connection_wrappers.logger"),
    ):
        manager = RedisConnectionManager()
        await manager.get_connection()
        await manager.close()

        assert manager._connection is None


@pytest.mark.asyncio
async def test_redis_connection_multiple_connect_close_cycles():
    """Test multiple connect/close cycles work correctly."""
    fake_client1 = _FakeRedisClient()
    fake_client2 = _FakeRedisClient()

    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        side_effect=[fake_client1, fake_client2],
    ):
        conn = RedisConnection()

        result1 = await conn.connect()
        assert result1 is fake_client1
        await conn.close()

        result2 = await conn.connect()
        assert result2 is fake_client2
        await conn.close()


@pytest.mark.asyncio
async def test_redis_connection_manager_multiple_get_close_cycles():
    """Test multiple get_connection/close cycles work correctly."""
    fake_client1 = _FakeRedisClient()
    fake_client2 = _FakeRedisClient()

    with patch(
        "common.redis_protocol.connection_wrappers.get_redis_client",
        new_callable=AsyncMock,
        side_effect=[fake_client1, fake_client2],
    ):
        manager = RedisConnectionManager()

        result1 = await manager.get_connection()
        assert result1 is fake_client1
        await manager.close()

        result2 = await manager.get_connection()
        assert result2 is fake_client2
        await manager.close()
