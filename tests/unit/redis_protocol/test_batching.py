"""Tests for batch processing manager."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.common.redis_protocol.batching import BatchManager


class TestBatchManagerInit:
    """Tests for BatchManager initialization."""

    @pytest.mark.asyncio
    async def test_init_stores_name(self) -> None:
        """Stores name."""

        async def process_batch(_items):
            pass

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=100,
            process_batch=process_batch,
            name="test_manager",
        )

        assert manager.name == "test_manager"

    @pytest.mark.asyncio
    async def test_init_creates_lock(self) -> None:
        """Creates asyncio lock."""

        async def process_batch(_items):
            pass

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=100,
            process_batch=process_batch,
        )

        assert isinstance(manager._lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_init_creates_collector(self) -> None:
        """Creates BatchCollector."""

        async def process_batch(_items):
            pass

        manager = BatchManager[int](
            batch_size=5,
            batch_time_ms=100,
            process_batch=process_batch,
        )

        assert manager._collector.batch_size == 5

    @pytest.mark.asyncio
    async def test_init_creates_executor(self) -> None:
        """Creates BatchExecutor."""

        async def process_batch(_items):
            pass

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=100,
            process_batch=process_batch,
        )

        assert manager._executor.process_batch == process_batch

    @pytest.mark.asyncio
    async def test_init_creates_timer(self) -> None:
        """Creates BatchTimer with correct time conversion."""

        async def process_batch(_items):
            pass

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=500,
            process_batch=process_batch,
        )

        assert manager._timer.batch_time_seconds == 0.5


class TestAddItem:
    """Tests for add_item method."""

    @pytest.mark.asyncio
    async def test_adds_item_to_collector(self) -> None:
        """Adds item to collector."""

        async def process_batch(_items):
            pass

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        await manager.add_item(42)

        assert 42 in manager._collector.current_batch

    @pytest.mark.asyncio
    async def test_starts_timer_on_first_item(self) -> None:
        """Starts timer when first item is added."""

        async def process_batch(_items):
            pass

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        await manager.add_item(1)
        await asyncio.sleep(0)

        assert manager._timer.is_running()

    @pytest.mark.asyncio
    async def test_processes_on_size_threshold(self) -> None:
        """Processes batch when size threshold reached."""
        processed_batches = []
        batch_processed = asyncio.Event()

        async def process_batch(items):
            processed_batches.append(list(items))
            batch_processed.set()

        manager = BatchManager[int](
            batch_size=3,
            batch_time_ms=1_000,
            process_batch=process_batch,
            name="size-threshold",
        )

        await manager.add_item(1)
        await manager.add_item(2)
        await manager.add_item(3)

        await asyncio.wait_for(batch_processed.wait(), timeout=1)

        assert processed_batches == [[1, 2, 3]]
        assert manager._collector.current_batch == []

    @pytest.mark.asyncio
    async def test_multiple_batches_on_size_threshold(self) -> None:
        """Processes multiple batches when size threshold reached."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        manager = BatchManager[int](
            batch_size=2,
            batch_time_ms=1_000,
            process_batch=process_batch,
        )

        await manager.add_item(1)
        await manager.add_item(2)
        await asyncio.sleep(0.01)

        await manager.add_item(3)
        await manager.add_item(4)
        await asyncio.sleep(0.01)

        assert processed_batches == [[1, 2], [3, 4]]


class TestTimerExpiration:
    """Tests for timer expiration behavior."""

    @pytest.mark.asyncio
    async def test_processes_on_time_threshold(self) -> None:
        """Processes batch when time threshold reached."""
        processed_batches = []
        batch_processed = asyncio.Event()

        async def process_batch(items):
            processed_batches.append(list(items))
            batch_processed.set()

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=50,
            process_batch=process_batch,
            name="time-threshold",
        )

        await manager.add_item(42)
        await asyncio.wait_for(batch_processed.wait(), timeout=1)

        assert processed_batches == [[42]]
        assert manager._collector.current_batch == []

    @pytest.mark.asyncio
    async def test_timer_callback_does_not_process_empty_batch(self) -> None:
        """Timer callback returns early if batch is empty."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=50,
            process_batch=process_batch,
        )

        await manager._on_timer_expired()

        assert processed_batches == []

    @pytest.mark.asyncio
    async def test_cancels_timer_when_size_triggered(self) -> None:
        """Cancels timer when size threshold triggers processing."""
        processed_batches = []
        batch_processed = asyncio.Event()

        async def process_batch(items):
            processed_batches.append(list(items))
            batch_processed.set()

        manager = BatchManager[int](
            batch_size=2,
            batch_time_ms=1_000,
            process_batch=process_batch,
            name="cancel-timer",
        )

        await manager.add_item(10)
        await asyncio.sleep(0)
        timer_task = manager._timer._task
        assert timer_task is not None

        await manager.add_item(20)
        await asyncio.wait_for(batch_processed.wait(), timeout=1)
        await asyncio.sleep(0)

        assert processed_batches == [[10, 20]]
        assert manager._collector.current_batch == []
        assert timer_task.done()


class TestFlush:
    """Tests for flush method."""

    @pytest.mark.asyncio
    async def test_flushes_remaining_items(self) -> None:
        """Flushes remaining items in batch."""
        processed_batches = []
        batch_processed = asyncio.Event()

        async def process_batch(items):
            processed_batches.append(list(items))
            batch_processed.set()

        manager = BatchManager[str](
            batch_size=5,
            batch_time_ms=1_000,
            process_batch=process_batch,
            name="flush-test",
        )

        await manager.add_item("alpha")
        await manager.add_item("beta")

        await manager.flush()
        await asyncio.wait_for(batch_processed.wait(), timeout=1)

        assert processed_batches == [["alpha", "beta"]]
        assert manager._collector.current_batch == []

    @pytest.mark.asyncio
    async def test_flush_with_empty_batch(self) -> None:
        """Flush does nothing when batch is empty."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        await manager.flush()

        assert processed_batches == []

    @pytest.mark.asyncio
    async def test_multiple_flushes(self) -> None:
        """Multiple flushes work correctly."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        await manager.add_item(1)
        await manager.flush()

        await manager.add_item(2)
        await manager.flush()

        assert processed_batches == [[1], [2]]


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_handles_runtime_error(self, caplog) -> None:
        """Handles RuntimeError in batch processing."""

        async def failing_batch(_items):
            raise RuntimeError("boom")

        manager = BatchManager[int](
            batch_size=1,
            batch_time_ms=100,
            process_batch=failing_batch,
            name="error-handler",
        )

        with caplog.at_level("ERROR"):
            await manager.add_item(1)

        assert manager._collector.current_batch == []
        assert any("Error processing batch" in str(record.msg) for record in caplog.records)

    @pytest.mark.asyncio
    async def test_handles_value_error(self) -> None:
        """Handles ValueError in batch processing."""

        async def failing_batch(_items):
            raise ValueError("invalid value")

        manager = BatchManager[int](
            batch_size=1,
            batch_time_ms=100,
            process_batch=failing_batch,
        )

        await manager.add_item(1)

        assert manager._collector.current_batch == []

    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        """Handles ConnectionError in batch processing."""

        async def failing_batch(_items):
            raise ConnectionError("connection lost")

        manager = BatchManager[int](
            batch_size=1,
            batch_time_ms=100,
            process_batch=failing_batch,
        )

        await manager.add_item(1)

        assert manager._collector.current_batch == []

    @pytest.mark.asyncio
    async def test_handles_os_error(self) -> None:
        """Handles OSError in batch processing."""

        async def failing_batch(_items):
            raise OSError("os error")

        manager = BatchManager[int](
            batch_size=1,
            batch_time_ms=100,
            process_batch=failing_batch,
        )

        await manager.add_item(1)

        assert manager._collector.current_batch == []

    @pytest.mark.asyncio
    async def test_reraises_cancelled_error(self) -> None:
        """Re-raises CancelledError."""

        async def failing_batch(_items):
            raise asyncio.CancelledError()

        manager = BatchManager[int](
            batch_size=1,
            batch_time_ms=100,
            process_batch=failing_batch,
        )

        with pytest.raises(asyncio.CancelledError):
            await manager.add_item(1)


class TestContextManager:
    """Tests for context manager protocol."""

    @pytest.mark.asyncio
    async def test_context_manager_flushes(monkeypatch) -> None:
        """Context manager flushes on exit."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        async with BatchManager[int](
            batch_size=5,
            batch_time_ms=5_000,
            process_batch=process_batch,
            name="context-manager",
        ) as manager:
            await manager.add_item(99)
            assert manager._collector.current_batch == [99]

        assert processed_batches == [[99]]
        assert manager._collector.current_batch == []
        if manager._timer._task is not None:
            assert manager._timer._task.done()

    @pytest.mark.asyncio
    async def test_context_manager_cancels_timer_on_exit(self) -> None:
        """Context manager cancels timer on exit."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        async with BatchManager[int](
            batch_size=10,
            batch_time_ms=1000,
            process_batch=process_batch,
        ) as manager:
            await manager.add_item(1)
            timer_task = manager._timer._task

        assert timer_task is not None
        assert timer_task.done()

    @pytest.mark.asyncio
    async def test_context_manager_logs_error_on_exception(self, caplog) -> None:
        """Context manager logs error when exception occurs."""

        async def process_batch(_items):
            pass

        def raise_error():
            raise ValueError("test error")

        with caplog.at_level("ERROR"):
            try:
                async with BatchManager[int](
                    batch_size=10,
                    batch_time_ms=1000,
                    process_batch=process_batch,
                    name="error-test",
                ) as _manager:
                    raise_error()
            except ValueError:
                pass

        assert any("error-test" in str(record.msg) for record in caplog.records)
        assert any("ValueError" in str(record.msg) for record in caplog.records)

    @pytest.mark.asyncio
    async def test_context_manager_returns_self(self) -> None:
        """Context manager returns self on enter."""

        async def process_batch(_items):
            pass

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        async with manager as ctx_manager:
            assert ctx_manager is manager


class TestGenericTypes:
    """Tests for generic type support."""

    @pytest.mark.asyncio
    async def test_works_with_string_type(self) -> None:
        """Works with string type."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        manager = BatchManager[str](
            batch_size=2,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        await manager.add_item("hello")
        await manager.add_item("world")

        await manager.flush()

        assert processed_batches == [["hello", "world"]]

    @pytest.mark.asyncio
    async def test_works_with_dict_type(self) -> None:
        """Works with dict type."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        manager = BatchManager[dict](
            batch_size=2,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        await manager.add_item({"key": "value1"})
        await manager.add_item({"key": "value2"})

        await manager.flush()

        assert processed_batches == [[{"key": "value1"}, {"key": "value2"}]]

    @pytest.mark.asyncio
    async def test_works_with_tuple_type(self) -> None:
        """Works with tuple type."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        manager = BatchManager[tuple](
            batch_size=2,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        await manager.add_item((1, 2))
        await manager.add_item((3, 4))

        await manager.flush()

        assert processed_batches == [[(1, 2), (3, 4)]]


class TestProcessCurrentBatch:
    """Tests for _process_current_batch internal method."""

    @pytest.mark.asyncio
    async def test_returns_early_when_no_items(self) -> None:
        """Returns early when batch has no items."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        manager = BatchManager[int](
            batch_size=10,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        await manager._process_current_batch("test reason")

        assert processed_batches == []

    @pytest.mark.asyncio
    async def test_clears_batch_on_error(self) -> None:
        """Clears batch when processing error occurs."""
        call_count = 0

        async def failing_batch(_items):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("fail")

        manager = BatchManager[int](
            batch_size=2,
            batch_time_ms=1000,
            process_batch=failing_batch,
        )

        await manager.add_item(1)
        await manager.add_item(2)
        await asyncio.sleep(0.01)

        assert len(manager._collector.current_batch) == 0
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cancels_timer_before_processing(self) -> None:
        """Cancels timer before processing batch."""
        processed = False

        async def process_batch(_items):
            nonlocal processed
            processed = True

        manager = BatchManager[int](
            batch_size=2,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        await manager.add_item(1)
        await asyncio.sleep(0)
        timer_task = manager._timer._task

        await manager.add_item(2)
        await asyncio.sleep(0)

        assert processed
        assert timer_task is not None
        assert timer_task.done()


class TestConcurrency:
    """Tests for concurrent operations."""

    @pytest.mark.asyncio
    async def test_add_item_is_thread_safe(self) -> None:
        """Multiple concurrent add_item calls are handled safely."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(len(items))
            await asyncio.sleep(0.01)

        manager = BatchManager[int](
            batch_size=5,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        tasks = [manager.add_item(i) for i in range(10)]
        await asyncio.gather(*tasks)

        await manager.flush()

        total_processed = sum(processed_batches)
        assert total_processed == 10

    @pytest.mark.asyncio
    async def test_sequential_batches(self) -> None:
        """Sequential batches are processed correctly."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(list(items))

        manager = BatchManager[int](
            batch_size=3,
            batch_time_ms=1000,
            process_batch=process_batch,
        )

        await manager.add_item(1)
        await manager.add_item(2)
        await manager.add_item(3)
        await asyncio.sleep(0.01)

        await manager.add_item(4)
        await manager.add_item(5)
        await manager.flush()

        assert processed_batches == [[1, 2, 3], [4, 5]]
