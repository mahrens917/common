import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from common.metadata_store_auto_updater_helpers.batch_processor import BatchProcessor


class TestBatchProcessor:
    @pytest.fixture
    def metadata_store(self):
        return AsyncMock()

    @pytest.fixture
    def batch_lock(self):
        return asyncio.Lock()

    @pytest.fixture
    def processor(self, metadata_store, batch_lock):
        return BatchProcessor(
            metadata_store=metadata_store,
            pending_updates={"service1": 5, "service2": 3},
            batch_lock=batch_lock,
            batch_interval_seconds=0.01,
        )

    @pytest.mark.asyncio
    async def test_run_processes_updates(self, processor, metadata_store):
        # Run the processor for a short time
        task = asyncio.create_task(processor.run())
        await asyncio.sleep(0.05)

        # Signal shutdown
        processor.request_shutdown()
        await asyncio.sleep(0.02)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Check that updates were processed
        assert processor.pending_updates == {}
        assert metadata_store.increment_service_count.call_count == 2
        metadata_store.increment_service_count.assert_any_call("service1", 5)
        metadata_store.increment_service_count.assert_any_call("service2", 3)

    @pytest.mark.asyncio
    async def test_run_with_empty_updates(self, processor, metadata_store):
        processor.pending_updates.clear()

        task = asyncio.create_task(processor.run())
        await asyncio.sleep(0.05)

        processor.request_shutdown()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert metadata_store.increment_service_count.call_count == 0

    @pytest.mark.asyncio
    async def test_shutdown_requested(self, processor, metadata_store):
        processor.request_shutdown()
        task = asyncio.create_task(processor.run())
        await asyncio.sleep(0.02)

        assert task.done()
        # Should not have processed anything if shutdown immediately (though wait might process once depending on timing, but here loop check is at start)
        # Actually, the loop condition is while not self._shutdown_requested.
        # Since we set it before run, it shouldn't run the body of the loop?
        # Wait, run() calls `await asyncio.sleep` first? No, `while not self._shutdown_requested`.
        # So it should exit immediately.
        assert metadata_store.increment_service_count.call_count == 0

    @pytest.mark.asyncio
    async def test_process_batched_updates_error(self, processor, metadata_store):
        metadata_store.increment_service_count.side_effect = Exception("Redis error")

        # Run manually
        await processor._process_batched_updates({"s1": 1})
        # Should log error but not raise
        metadata_store.increment_service_count.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_handles_redis_error(self, processor, metadata_store):
        # Mock _process_batched_updates to raise exception
        processor._process_batched_updates = AsyncMock(side_effect=Exception("Processing Error"))

        task = asyncio.create_task(processor.run())
        await asyncio.sleep(0.05)
        processor.request_shutdown()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should continue running despite error, until shutdown
        # We can verify it tried to process
        assert processor._process_batched_updates.called
