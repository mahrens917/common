"""Tests for callback executor."""

from __future__ import annotations

import asyncio

import pytest

from common.dependency_monitor_helpers.callback_executor import CallbackExecutor


class TestCaptureAsyncResult:
    """Tests for _capture_async_result method."""

    @pytest.mark.asyncio
    async def test_captures_successful_result(self) -> None:
        """Captures result from successful awaitable."""

        async def success() -> str:
            return "success"

        executor = CallbackExecutor()
        result, error = await executor._capture_async_result(success())

        assert result == "success"
        assert error is None

    @pytest.mark.asyncio
    async def test_captures_exception(self) -> None:
        """Captures exception from failing awaitable."""

        async def failure() -> str:
            raise ValueError("test error")

        executor = CallbackExecutor()
        result, error = await executor._capture_async_result(failure())

        assert result is None
        assert isinstance(error, ValueError)
        assert str(error) == "test error"


class TestInvokeCheckFunction:
    """Tests for invoke_check_function method."""

    @pytest.mark.asyncio
    async def test_invokes_async_function(self) -> None:
        """Invokes async check function."""

        async def async_check() -> int:
            return 42

        executor = CallbackExecutor()
        result, error = await executor.invoke_check_function(async_check)

        assert result == 42
        assert error is None

    @pytest.mark.asyncio
    async def test_invokes_sync_function(self) -> None:
        """Invokes sync check function in thread."""

        def sync_check() -> str:
            return "sync_result"

        executor = CallbackExecutor()
        result, error = await executor.invoke_check_function(sync_check)

        assert result == "sync_result"
        assert error is None

    @pytest.mark.asyncio
    async def test_captures_async_function_error(self) -> None:
        """Captures error from async check function."""

        async def async_error() -> None:
            raise RuntimeError("async error")

        executor = CallbackExecutor()
        result, error = await executor.invoke_check_function(async_error)

        assert result is None
        assert isinstance(error, RuntimeError)

    @pytest.mark.asyncio
    async def test_captures_sync_function_error(self) -> None:
        """Captures error from sync check function."""

        def sync_error() -> None:
            raise TypeError("sync error")

        executor = CallbackExecutor()
        result, error = await executor.invoke_check_function(sync_error)

        assert result is None
        assert isinstance(error, TypeError)


class TestRunCallback:
    """Tests for run_callback method."""

    @pytest.mark.asyncio
    async def test_runs_async_callback_success(self) -> None:
        """Runs async callback successfully."""

        async def async_callback() -> None:
            pass

        executor = CallbackExecutor()
        error = await executor.run_callback(async_callback)

        assert error is None

    @pytest.mark.asyncio
    async def test_runs_async_callback_failure(self) -> None:
        """Runs async callback and captures error."""

        async def async_callback_error() -> None:
            raise ValueError("callback error")

        executor = CallbackExecutor()
        error = await executor.run_callback(async_callback_error)

        assert isinstance(error, ValueError)
        assert str(error) == "callback error"

    @pytest.mark.asyncio
    async def test_runs_sync_callback_success(self) -> None:
        """Runs sync callback successfully in thread."""

        def sync_callback() -> None:
            pass

        executor = CallbackExecutor()
        error = await executor.run_callback(sync_callback)

        assert error is None

    @pytest.mark.asyncio
    async def test_runs_sync_callback_failure(self) -> None:
        """Runs sync callback and captures error."""

        def sync_callback_error() -> None:
            raise RuntimeError("sync callback error")

        executor = CallbackExecutor()
        error = await executor.run_callback(sync_callback_error)

        assert isinstance(error, RuntimeError)

    @pytest.mark.asyncio
    async def test_runs_callable_with_async_func_attribute(self) -> None:
        """Runs callable with async func attribute."""

        class CallableWithFunc:
            async def func(self) -> None:
                pass

            async def __call__(self) -> None:
                await self.func()

        callback = CallableWithFunc()
        executor = CallbackExecutor()
        error = await executor.run_callback(callback)

        assert error is None

    @pytest.mark.asyncio
    async def test_runs_callable_with_async_call_method(self) -> None:
        """Runs callable with async __call__ method."""

        class AsyncCallable:
            async def __call__(self) -> None:
                pass

        callback = AsyncCallable()
        executor = CallbackExecutor()
        error = await executor.run_callback(callback)

        assert error is None
