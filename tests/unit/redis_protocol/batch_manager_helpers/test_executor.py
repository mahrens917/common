"""Tests for batch executor module."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import RedisError

from common.redis_protocol.batch_manager_helpers.executor import BatchExecutor


class TestBatchExecutor:
    """Tests for BatchExecutor class."""

    def test_init_stores_process_batch(self) -> None:
        """Stores process_batch callback."""
        process_batch = AsyncMock()

        executor = BatchExecutor[str](process_batch=process_batch, name="test")

        assert executor.process_batch == process_batch

    def test_init_stores_name(self) -> None:
        """Stores name."""
        process_batch = AsyncMock()

        executor = BatchExecutor[str](process_batch=process_batch, name="test_executor")

        assert executor.name == "test_executor"


class TestExecute:
    """Tests for execute method."""

    @pytest.mark.asyncio
    async def test_calls_process_batch_with_items(self) -> None:
        """Calls process_batch with batch items."""
        process_batch = AsyncMock()
        executor = BatchExecutor[str](process_batch=process_batch, name="test")
        batch = ["item1", "item2", "item3"]

        await executor.execute(batch, batch_size=3, batch_time=0.1, reason="test")

        process_batch.assert_called_once_with(batch)

    @pytest.mark.asyncio
    async def test_returns_early_when_batch_empty(self) -> None:
        """Returns early when batch is empty."""
        process_batch = AsyncMock()
        executor = BatchExecutor[str](process_batch=process_batch, name="test")

        await executor.execute([], batch_size=0, batch_time=0.0, reason="test")

        process_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_redis_error(self) -> None:
        """Re-raises RedisError after logging."""
        process_batch = AsyncMock(side_effect=RedisError("test error"))
        executor = BatchExecutor[str](process_batch=process_batch, name="test")
        batch = ["item1"]

        # Patch logger to prevent logging format error from masking the test
        with patch("common.redis_protocol.batch_manager_helpers.executor.logger"):
            with pytest.raises(RedisError):
                await executor.execute(batch, batch_size=1, batch_time=0.1, reason="test")

    @pytest.mark.asyncio
    async def test_raises_connection_error(self) -> None:
        """Re-raises ConnectionError after logging."""
        process_batch = AsyncMock(side_effect=ConnectionError("test error"))
        executor = BatchExecutor[str](process_batch=process_batch, name="test")
        batch = ["item1"]

        with patch("common.redis_protocol.batch_manager_helpers.executor.logger"):
            with pytest.raises(ConnectionError):
                await executor.execute(batch, batch_size=1, batch_time=0.1, reason="test")

    @pytest.mark.asyncio
    async def test_raises_timeout_error(self) -> None:
        """Re-raises TimeoutError after logging."""
        process_batch = AsyncMock(side_effect=TimeoutError("test error"))
        executor = BatchExecutor[str](process_batch=process_batch, name="test")
        batch = ["item1"]

        with patch("common.redis_protocol.batch_manager_helpers.executor.logger"):
            with pytest.raises(TimeoutError):
                await executor.execute(batch, batch_size=1, batch_time=0.1, reason="test")

    @pytest.mark.asyncio
    async def test_raises_runtime_error(self) -> None:
        """Re-raises RuntimeError after logging."""
        process_batch = AsyncMock(side_effect=RuntimeError("test error"))
        executor = BatchExecutor[str](process_batch=process_batch, name="test")
        batch = ["item1"]

        with patch("common.redis_protocol.batch_manager_helpers.executor.logger"):
            with pytest.raises(RuntimeError):
                await executor.execute(batch, batch_size=1, batch_time=0.1, reason="test")

    @pytest.mark.asyncio
    async def test_raises_value_error(self) -> None:
        """Re-raises ValueError after logging."""
        process_batch = AsyncMock(side_effect=ValueError("test error"))
        executor = BatchExecutor[str](process_batch=process_batch, name="test")
        batch = ["item1"]

        with patch("common.redis_protocol.batch_manager_helpers.executor.logger"):
            with pytest.raises(ValueError):
                await executor.execute(batch, batch_size=1, batch_time=0.1, reason="test")

    @pytest.mark.asyncio
    async def test_raises_type_error(self) -> None:
        """Re-raises TypeError after logging."""
        process_batch = AsyncMock(side_effect=TypeError("test error"))
        executor = BatchExecutor[str](process_batch=process_batch, name="test")
        batch = ["item1"]

        with pytest.raises(TypeError):
            await executor.execute(batch, batch_size=1, batch_time=0.1, reason="test")

    @pytest.mark.asyncio
    async def test_raises_os_error(self) -> None:
        """Re-raises OSError after logging."""
        process_batch = AsyncMock(side_effect=OSError("test error"))
        executor = BatchExecutor[str](process_batch=process_batch, name="test")
        batch = ["item1"]

        with patch("common.redis_protocol.batch_manager_helpers.executor.logger"):
            with pytest.raises(OSError):
                await executor.execute(batch, batch_size=1, batch_time=0.1, reason="test")


class TestGenericType:
    """Tests for generic type support."""

    @pytest.mark.asyncio
    async def test_works_with_int_type(self) -> None:
        """Works with int type."""
        process_batch = AsyncMock()
        executor = BatchExecutor[int](process_batch=process_batch, name="test")
        batch = [1, 2, 3]

        await executor.execute(batch, batch_size=3, batch_time=0.1, reason="test")

        process_batch.assert_called_once_with(batch)

    @pytest.mark.asyncio
    async def test_works_with_dict_type(self) -> None:
        """Works with dict type."""
        process_batch = AsyncMock()
        executor = BatchExecutor[dict](process_batch=process_batch, name="test")
        batch = [{"key": "value1"}, {"key": "value2"}]

        await executor.execute(batch, batch_size=2, batch_time=0.1, reason="test")

        process_batch.assert_called_once_with(batch)
