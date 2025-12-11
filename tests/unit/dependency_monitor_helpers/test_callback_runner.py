"""Tests for CallbackRunner."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.dependency_monitor_helpers.callback_runner import CallbackRunner


class TestCallbackRunner:
    """Tests for CallbackRunner class."""

    @pytest.mark.asyncio
    async def test_runs_single_callback_successfully(self) -> None:
        """Runs a single callback successfully."""
        callback = MagicMock()
        executor = MagicMock()
        executor.run_callback = AsyncMock(return_value=None)

        await CallbackRunner.run_callbacks([callback], "test_service", executor)

        executor.run_callback.assert_called_once_with(callback)

    @pytest.mark.asyncio
    async def test_runs_multiple_callbacks_successfully(self) -> None:
        """Runs multiple callbacks successfully."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        callback3 = MagicMock()
        executor = MagicMock()
        executor.run_callback = AsyncMock(return_value=None)

        await CallbackRunner.run_callbacks([callback1, callback2, callback3], "test_service", executor)

        assert executor.run_callback.call_count == 3
        executor.run_callback.assert_any_call(callback1)
        executor.run_callback.assert_any_call(callback2)
        executor.run_callback.assert_any_call(callback3)

    @pytest.mark.asyncio
    async def test_runs_empty_callback_list(self) -> None:
        """Runs successfully with empty callback list."""
        executor = MagicMock()
        executor.run_callback = AsyncMock(return_value=None)

        await CallbackRunner.run_callbacks([], "test_service", executor)

        executor.run_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_continues_after_runtime_error(self) -> None:
        """Continues to next callback after RuntimeError."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        executor = MagicMock()
        executor.run_callback = AsyncMock(side_effect=[RuntimeError("error"), None])

        await CallbackRunner.run_callbacks([callback1, callback2], "test_service", executor)

        assert executor.run_callback.call_count == 2

    @pytest.mark.asyncio
    async def test_continues_after_value_error(self) -> None:
        """Continues to next callback after ValueError."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        executor = MagicMock()
        executor.run_callback = AsyncMock(side_effect=[ValueError("error"), None])

        await CallbackRunner.run_callbacks([callback1, callback2], "test_service", executor)

        assert executor.run_callback.call_count == 2

    @pytest.mark.asyncio
    async def test_continues_after_type_error(self) -> None:
        """Continues to next callback after TypeError."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        executor = MagicMock()
        executor.run_callback = AsyncMock(side_effect=[TypeError("error"), None])

        await CallbackRunner.run_callbacks([callback1, callback2], "test_service", executor)

        assert executor.run_callback.call_count == 2

    @pytest.mark.asyncio
    async def test_continues_after_attribute_error(self) -> None:
        """Continues to next callback after AttributeError."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        executor = MagicMock()
        executor.run_callback = AsyncMock(side_effect=[AttributeError("error"), None])

        await CallbackRunner.run_callbacks([callback1, callback2], "test_service", executor)

        assert executor.run_callback.call_count == 2

    @pytest.mark.asyncio
    async def test_continues_after_os_error(self) -> None:
        """Continues to next callback after OSError."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        executor = MagicMock()
        executor.run_callback = AsyncMock(side_effect=[OSError("error"), None])

        await CallbackRunner.run_callbacks([callback1, callback2], "test_service", executor)

        assert executor.run_callback.call_count == 2

    @pytest.mark.asyncio
    async def test_continues_after_key_error(self) -> None:
        """Continues to next callback after KeyError."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        executor = MagicMock()
        executor.run_callback = AsyncMock(side_effect=[KeyError("error"), None])

        await CallbackRunner.run_callbacks([callback1, callback2], "test_service", executor)

        assert executor.run_callback.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_cancelled_error(self) -> None:
        """Raises CancelledError without catching it."""
        callback = MagicMock()
        executor = MagicMock()
        executor.run_callback = AsyncMock(side_effect=asyncio.CancelledError())

        with pytest.raises(asyncio.CancelledError):
            await CallbackRunner.run_callbacks([callback], "test_service", executor)

    @pytest.mark.asyncio
    async def test_logs_error_when_callback_returns_exception(self) -> None:
        """Logs error when callback returns an exception."""
        callback = MagicMock()
        executor = MagicMock()
        returned_error = RuntimeError("callback error")
        executor.run_callback = AsyncMock(return_value=returned_error)

        await CallbackRunner.run_callbacks([callback], "test_service", executor)

        # Should complete without raising
        executor.run_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_multiple_errors_in_sequence(self) -> None:
        """Handles multiple errors and continues."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        callback3 = MagicMock()
        executor = MagicMock()
        executor.run_callback = AsyncMock(
            side_effect=[
                RuntimeError("error1"),
                ValueError("error2"),
                None,
            ]
        )

        await CallbackRunner.run_callbacks([callback1, callback2, callback3], "test_service", executor)

        assert executor.run_callback.call_count == 3
