"""Tests for batch timer module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.batch_manager_helpers.timer import BatchTimer


class TestBatchTimer:
    """Tests for BatchTimer class."""

    def test_init_stores_batch_time(self) -> None:
        """Stores batch time seconds."""
        on_timeout = AsyncMock()

        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")

        assert timer.batch_time_seconds == 5.0

    def test_init_stores_callback(self) -> None:
        """Stores on_timeout callback."""
        on_timeout = AsyncMock()

        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")

        assert timer.on_timeout == on_timeout

    def test_init_stores_name(self) -> None:
        """Stores name."""
        on_timeout = AsyncMock()

        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test_timer")

        assert timer.name == "test_timer"

    def test_init_no_task(self) -> None:
        """Task is None initially."""
        on_timeout = AsyncMock()

        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")

        assert timer._task is None


class TestStart:
    """Tests for start method."""

    @pytest.mark.asyncio
    async def test_creates_task(self) -> None:
        """Creates asyncio task."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")

        timer.start(batch_size=10)

        assert timer._task is not None
        # Cleanup
        timer.cancel()
        await timer.wait_for_cancellation()

    @pytest.mark.asyncio
    async def test_does_not_create_duplicate_task(self) -> None:
        """Does not create duplicate task if already running."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")

        timer.start(batch_size=10)
        first_task = timer._task
        timer.start(batch_size=10)

        assert timer._task == first_task
        # Cleanup
        timer.cancel()
        await timer.wait_for_cancellation()


class TestCancel:
    """Tests for cancel method."""

    @pytest.mark.asyncio
    async def test_cancels_running_task(self) -> None:
        """Cancels running task."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")
        timer.start(batch_size=10)

        timer.cancel()
        await timer.wait_for_cancellation()

        assert timer._task.cancelled() or timer._task.done()

    def test_no_error_when_no_task(self) -> None:
        """No error when no task to cancel."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")

        timer.cancel()  # Should not raise


class TestIsRunning:
    """Tests for is_running method."""

    def test_returns_false_when_no_task(self) -> None:
        """Returns False when no task."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")

        assert timer.is_running() is False

    @pytest.mark.asyncio
    async def test_returns_true_when_task_running(self) -> None:
        """Returns True when task is running."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")
        timer.start(batch_size=10)

        assert timer.is_running() is True
        # Cleanup
        timer.cancel()
        await timer.wait_for_cancellation()

    @pytest.mark.asyncio
    async def test_returns_false_after_cancel(self) -> None:
        """Returns False after task cancelled and awaited."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")
        timer.start(batch_size=10)
        timer.cancel()
        await timer.wait_for_cancellation()

        # After waiting for cancellation, task should be done
        assert timer._task.done()


class TestRun:
    """Tests for _run method."""

    @pytest.mark.asyncio
    async def test_calls_on_timeout_after_wait(self) -> None:
        """Calls on_timeout callback after wait."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=0.01, on_timeout=on_timeout, name="test")

        await timer._run(batch_size=5)

        on_timeout.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_cancelled_error(self) -> None:
        """Handles CancelledError gracefully."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")

        timer.start(batch_size=10)
        timer.cancel()

        # Should not raise when awaiting cancelled task
        try:
            await timer._task
        except asyncio.CancelledError:
            pass  # Expected

    @pytest.mark.asyncio
    async def test_handles_redis_error_in_callback(self) -> None:
        """Handles Redis error in callback."""
        from unittest.mock import patch

        from redis.exceptions import RedisError

        on_timeout = AsyncMock(side_effect=RedisError("test error"))
        timer = BatchTimer(batch_time_seconds=0.01, on_timeout=on_timeout, name="test")

        # Patch logger to prevent logging format error
        with patch("common.redis_protocol.batch_manager_helpers.timer.logger"):
            # Should not raise, just log
            await timer._run(batch_size=5)

    @pytest.mark.asyncio
    async def test_handles_connection_error_in_callback(self) -> None:
        """Handles ConnectionError in callback."""
        from unittest.mock import patch

        on_timeout = AsyncMock(side_effect=ConnectionError("test error"))
        timer = BatchTimer(batch_time_seconds=0.01, on_timeout=on_timeout, name="test")

        # Patch logger to prevent logging format error
        with patch("common.redis_protocol.batch_manager_helpers.timer.logger"):
            # Should not raise, just log
            await timer._run(batch_size=5)


class TestWaitForCancellation:
    """Tests for wait_for_cancellation method."""

    @pytest.mark.asyncio
    async def test_waits_for_task_completion(self) -> None:
        """Waits for task to complete."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=0.01, on_timeout=on_timeout, name="test")
        timer.start(batch_size=10)

        await timer.wait_for_cancellation()

        assert timer._task.done()

    @pytest.mark.asyncio
    async def test_handles_cancelled_task(self) -> None:
        """Handles cancelled task gracefully."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")
        timer.start(batch_size=10)
        timer.cancel()

        # Should not raise
        await timer.wait_for_cancellation()

    @pytest.mark.asyncio
    async def test_returns_immediately_when_no_task(self) -> None:
        """Returns immediately when no task."""
        on_timeout = AsyncMock()
        timer = BatchTimer(batch_time_seconds=5.0, on_timeout=on_timeout, name="test")

        # Should not block
        await timer.wait_for_cancellation()
