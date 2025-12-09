from __future__ import annotations

"""Utility helpers for scheduling asyncio coroutines safely."""

import asyncio
from typing import Any, Callable, Coroutine, Optional, Union

CoroutineFactory = Callable[[], Coroutine[Any, Any, Any]]


def safely_schedule_coroutine(
    coro_or_factory: Union[Coroutine[Any, Any, Any], CoroutineFactory],
) -> Optional[asyncio.Task[Any]]:
    """
    Schedule the provided coroutine even when ``asyncio.create_task`` is patched.

    Accept either a coroutine object or a zero-argument callable that returns a
    coroutine, which prevents creating the coroutine unless scheduling actually
    happens.
    """
    coro = _resolve_coroutine(coro_or_factory)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
        return None

    try:
        return loop.create_task(coro)
    except (RuntimeError, ValueError, TypeError):
        asyncio.run(coro)
        return None


def _resolve_coroutine(
    coro_or_factory: Union[Coroutine[Any, Any, Any], CoroutineFactory],
) -> Coroutine[Any, Any, Any]:
    """Turn the input into a coroutine object for scheduling."""
    if asyncio.iscoroutine(coro_or_factory):
        return coro_or_factory

    if callable(coro_or_factory):
        result = coro_or_factory()
        if not asyncio.iscoroutine(result):
            raise TypeError("Callable passed to safely_schedule_coroutine must return a coroutine")
        return result

    raise TypeError("safely_schedule_coroutine expects a coroutine or a callable returning one")
