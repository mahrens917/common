"""Tests for src/common/async_helpers.py."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from common.async_helpers import _resolve_coroutine, bounded_gather, safely_schedule_coroutine


async def sample_coro():
    """Sample coroutine for testing."""
    return "success"


def sample_factory():
    """Sample factory that returns a coroutine."""
    return sample_coro()


def invalid_factory():
    """Factory that returns a non-coroutine."""
    return "not_a_coroutine"


class TestResolveCoroutine:
    """Tests for _resolve_coroutine helper."""

    def test_returns_coroutine_directly(self):
        """A coroutine object is returned unchanged."""
        coro = sample_coro()
        result = _resolve_coroutine(coro)
        assert asyncio.iscoroutine(result)
        # Clean up coroutine to avoid warning
        result.close()

    def test_calls_factory_and_returns_result(self):
        """A callable factory is invoked and its coroutine returned."""
        result = _resolve_coroutine(sample_factory)
        assert asyncio.iscoroutine(result)
        result.close()

    def test_raises_for_factory_returning_non_coroutine(self):
        """TypeError raised when factory returns non-coroutine."""
        with pytest.raises(TypeError, match="must return a coroutine"):
            _resolve_coroutine(invalid_factory)

    def test_raises_for_invalid_input(self):
        """TypeError raised for non-coroutine non-callable input."""
        with pytest.raises(TypeError, match="expects a coroutine or a callable"):
            _resolve_coroutine("not_valid")


class TestSafelyScheduleCoroutine:
    """Tests for safely_schedule_coroutine function."""

    @pytest.mark.asyncio
    async def test_schedules_coroutine_with_running_loop(self):
        """With a running loop, create_task is used to schedule the coroutine."""
        task = safely_schedule_coroutine(sample_coro())
        assert isinstance(task, asyncio.Task)
        result = await task
        assert result == "success"

    @pytest.mark.asyncio
    async def test_schedules_factory_with_running_loop(self):
        """A factory is resolved and scheduled with a running loop."""
        task = safely_schedule_coroutine(sample_factory)
        assert isinstance(task, asyncio.Task)
        result = await task
        assert result == "success"

    def test_runs_with_asyncio_run_when_no_loop(self):
        """When no event loop is running, asyncio.run is used."""
        result_holder = {}

        async def capturing_coro():
            result_holder["executed"] = True
            return "done"

        # Ensure no running loop (test runs outside async context)
        task = safely_schedule_coroutine(capturing_coro())
        assert task is None
        assert result_holder.get("executed") is True

    def test_propagates_runtime_error_from_create_task(self):
        """RuntimeError during create_task propagates to the caller."""

        async def tracking_coro():
            pass

        mock_loop = MagicMock()
        mock_loop.create_task.side_effect = RuntimeError("test error")

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            coro = tracking_coro()
            with pytest.raises(RuntimeError, match="test error"):
                safely_schedule_coroutine(coro)
            coro.close()

    def test_propagates_value_error_from_create_task(self):
        """ValueError during create_task propagates to the caller."""

        async def simple_coro():
            return "ok"

        mock_loop = MagicMock()
        mock_loop.create_task.side_effect = ValueError("test error")

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            coro = simple_coro()
            with pytest.raises(ValueError, match="test error"):
                safely_schedule_coroutine(coro)
            coro.close()

    def test_propagates_type_error_from_create_task(self):
        """TypeError during create_task propagates to the caller."""

        async def simple_coro():
            return "ok"

        mock_loop = MagicMock()
        mock_loop.create_task.side_effect = TypeError("test error")

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            coro = simple_coro()
            with pytest.raises(TypeError, match="test error"):
                safely_schedule_coroutine(coro)
            coro.close()


class TestBoundedGather:
    """Tests for bounded_gather function."""

    @pytest.mark.asyncio
    async def test_returns_results_in_order(self):
        """Results are returned in the same order as the input coroutines."""

        async def identity(value: int) -> int:
            return value

        results = await bounded_gather((identity(i) for i in range(5)), max_concurrency=3)
        assert results == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_list(self):
        """Empty coroutine iterable returns an empty list."""
        results = await bounded_gather([], max_concurrency=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_respects_concurrency_limit(self):
        """No more than max_concurrency coroutines run simultaneously."""
        active = 0
        peak = 0

        async def track() -> None:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0)
            active -= 1

        await bounded_gather((track() for _ in range(10)), max_concurrency=3)
        assert peak <= 3

    @pytest.mark.asyncio
    async def test_single_concurrency_serializes(self):
        """max_concurrency=1 forces sequential execution."""
        order: list[int] = []

        async def record(i: int) -> None:
            order.append(i)
            await asyncio.sleep(0)

        await bounded_gather((record(i) for i in range(4)), max_concurrency=1)
        assert order == [0, 1, 2, 3]
