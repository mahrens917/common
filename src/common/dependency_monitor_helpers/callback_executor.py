"""Callback execution helper for dependency monitor."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


class CallbackExecutor:
    """Handles async/sync callback execution for dependency monitor."""

    @staticmethod
    async def _capture_async_result(
        awaitable: Awaitable[Any],
    ) -> tuple[Optional[Any], Optional[BaseException]]:
        """Capture result or exception from awaitable."""
        (result,) = await asyncio.gather(awaitable, return_exceptions=True)
        if isinstance(result, BaseException):
            return None, result
        return result, None

    async def invoke_check_function(self, check_function: Callable[[], Any]) -> tuple[Optional[Any], Optional[BaseException]]:
        """
        Invoke check function (async or sync).

        Args:
            check_function: Function to invoke

        Returns:
            Tuple of (result, error)
        """
        if asyncio.iscoroutinefunction(check_function):
            return await self._capture_async_result(check_function())
        return await self._capture_async_result(asyncio.to_thread(check_function))

    async def run_callback(self, callback: Callable[[], Any]) -> Optional[BaseException]:
        """
        Run callback (async or sync).

        Args:
            callback: Callback to run

        Returns:
            Error if callback failed, None otherwise
        """
        if asyncio.iscoroutinefunction(callback):
            _, error = await self._capture_async_result(callback())
            return error

        if hasattr(callback, "func") and asyncio.iscoroutinefunction(getattr(callback, "func")):
            _, error = await self._capture_async_result(callback())
            return error

        call_method = getattr(callback, "__call__", None)
        if call_method and asyncio.iscoroutinefunction(call_method):
            _, error = await self._capture_async_result(callback())
            return error

        _, error = await self._capture_async_result(asyncio.to_thread(callback))
        return error
