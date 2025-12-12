"""Tests for src/common/async_helpers.py."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from common.async_helpers import _resolve_coroutine, safely_schedule_coroutine


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

    def test_handles_runtime_error_in_create_task(self):
        """RuntimeError during create_task falls back to asyncio.run."""
        executed = {"count": 0}

        async def tracking_coro():
            executed["count"] += 1

        # Patch get_running_loop to return a mock, then create_task to raise
        mock_loop = MagicMock()
        mock_loop.create_task.side_effect = RuntimeError("test error")

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with patch("asyncio.run") as mock_run:
                result = safely_schedule_coroutine(tracking_coro())
                assert result is None
                assert mock_run.called

    def test_handles_value_error_in_create_task(self):
        """ValueError during create_task falls back to asyncio.run."""

        async def simple_coro():
            return "ok"

        mock_loop = MagicMock()
        mock_loop.create_task.side_effect = ValueError("test error")

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with patch("asyncio.run") as mock_run:
                result = safely_schedule_coroutine(simple_coro())
                assert result is None
                assert mock_run.called

    def test_handles_type_error_in_create_task(self):
        """TypeError during create_task falls back to asyncio.run."""

        async def simple_coro():
            return "ok"

        mock_loop = MagicMock()
        mock_loop.create_task.side_effect = TypeError("test error")

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with patch("asyncio.run") as mock_run:
                result = safely_schedule_coroutine(simple_coro())
                assert result is None
                assert mock_run.called
